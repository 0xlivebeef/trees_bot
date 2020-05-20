import os
import re
import csv
import sys
import math
import praw
import time
import calendar
import threading
import logging
from datetime import datetime, timedelta
from praw.models import Message
from praw.models import Comment
from praw.models import Submission
from praw.models.reddit.subreddit import SubredditModeration

sys.path.append(os.path.abspath('..'))
import config

# consts
WAIT = 56 # waiting time between update passes (in seconds)

# logging
LOG_FORMAT = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('local')

class Bot():
    
    reddit = praw.Reddit(
            client_id = config.CLIENT_ID,
            client_secret = config.CLIENT_SECRET,
            user_agent = config.USER_AGENT,
            username = config.USERNAME,
            password = config.PASSWORD
    )
    sub = reddit.subreddit(config.SUBREDDIT)
    modSub = reddit.subreddit(config.MOD_SUBREDDIT)
    testSub = reddit.subreddit(config.TEST_SUBREDDIT)

    def __init__(self):
        # print(sub.mod.settings())
        self.curDay = datetime.now().isoweekday()
        logfile_name_format = datetime.now().strftime("log_%Y-%m-%d")
        
        # Set up logging
        logger.setLevel(logging.DEBUG)
        self.fh = logging.FileHandler('../logfiles/' + logfile_name_format + '.txt')
        self.fh.setLevel(logging.DEBUG)
        self.fh.setFormatter(LOG_FORMAT)
        self.ch = logging.StreamHandler()
        self.ch.setLevel(logging.INFO)
        self.ch.setFormatter(LOG_FORMAT)
        logger.addHandler(self.fh)
        logger.addHandler(self.ch)
        logger.info("Bot initialized for /r/" + config.SUBREDDIT + " as /u/"
                    + config.USERNAME)
        self.initTime = datetime.now()
        modSubThread = threading.Thread(target=self.scanModSubreddit)
        inboxThread = threading.Thread(target=self.scanInbox)
        modSubThread.start()
        inboxThread.start()
        logger.info("Treesmods thread started")
        
        # 420
        self.lastTz = -1

    def run(self):
        # do initial stylesheet update pass
        newDay = datetime.now().isoweekday()
        self.dayChange(newDay)
        
        while True:
            logger.debug("begin scheduled tasks")
            newDay = datetime.now().isoweekday()
            if newDay != self.curDay:
                self.dayChange(newDay)
            logger.debug("end scheduled tasks")
            time.sleep(WAIT)
        logger.info('log hit run')
        print('hit run()')
        
    def dayChange(self, newDay):
        """
        This function activates and de-activates the /r/trees
        weekend stylesheet. It finds a specified block of code, and
        either inserts or removes CSS comment markers based on the day
        of the week.
        """
        style = self.sub.stylesheet
        css = self.sub.stylesheet().stylesheet
        curTime = datetime.now().strftime(
                "%b %d %Y %H:%M:%S EST (UTC-5)")
        
        if newDay == 1:  # MONDAY
            SubredditModeration(self.sub).update(link_type = 'any')
            css = re.sub(r'\*  BEGIN AUTOMATIC UPDATE AREA\n \*/\n\n',
                         '*  BEGIN AUTOMATIC UPDATE AREA\n */\n/*\n', css)
            css = re.sub(r'\n/\*\n \*  END AUTOMATIC UPDATE AREA',
                         '*/\n/*\n *  END AUTOMATIC UPDATE AREA', css)
            style.delete_banner_additional_image()
            style.upload_banner_additional_image('../img/banner-redesign-week.png', align="centered")
            style.delete_mobile_header()
            style.upload_mobile_header('../img/banner-mobile-week.png')
        
        if newDay == 6:  # SATURDAY
            css = re.sub(r'\*  BEGIN AUTOMATIC UPDATE AREA\n \*\/\n\/\*\n',
                         '*  BEGIN AUTOMATIC UPDATE AREA\n */\n\n', css)
            css = re.sub(r'%%sunday%%', '%%saturday%%', css)
            css = re.sub(r'\*\/\n\/\*\n \*  END AUTOMATIC UPDATE AREA',
                         '\n/*\n *  END AUTOMATIC UPDATE AREA', css)
            style.delete_banner_additional_image()
            style.upload_banner_additional_image('../img/banner-redesign-saturday.png', align="centered")
            style.delete_mobile_header()
            style.upload_mobile_header('../img/header-mobile-saturday.png')
            
        if newDay == 7:  # SUNDAY
            css = re.sub(r'%%saturday%%', '%%sunday%%', css)
            SubredditModeration(self.sub).update(link_type = 'self')
            style.delete_banner_additional_image()
            style.upload_banner_additional_image('../img/banner-redesign-sunday.png', align="centered")
            style.delete_mobile_header()
            style.upload_mobile_header('../img/header-mobile-sunday.png')
        
        if newDay in (1, 6, 7):
            newCSS = re.sub(r'  last change:.*.\n', '  last change: ' + curTime
                            + '\n', css)
            self.sub.stylesheet.update(newCSS,
                                        'scheduled stylesheet update for '
                                        + calendar.day_name[newDay-1])
            logger.info("Stylesheet successfully updated.")
    
        self.curDay = newDay
        self.logfile_name_format = datetime.now().strftime(
                "log_%Y-%m-%d")
        logger.removeHandler(self.fh)
        self.fh = logging.FileHandler('../logfiles/' + self.logfile_name_format
                                      + '.txt')
        self.fh.setFormatter(LOG_FORMAT)
        logger.addHandler(self.fh)
        
                       
    def scanModSubreddit(self):
        """
        Scans for new posts in a given mods-only subreddit, and relays new
        posts to the mod team
        """
        while True:
            try:
                modSubmissions = self.modSub.stream.submissions();
                for submission in modSubmissions:
                    if (datetime.fromtimestamp(submission.created) > self.initTime):
                        alreadyExists = False
                        with open('../treesmodspostids.txt', 'r') as f:
                            for line in f.readlines():
                                if (line.strip() == submission.id):
                                    alreadyExists = True
                                    break
                        if (not alreadyExists):
                            logger.info('New post detected in /r/' + self.modSub.display_name)
                            for moderator in self.sub.moderator():
                                moderator.message(submission.author.name + ' has added a new post in'
                                                    + ' /r/' + self.modSub.display_name,
                                                 '[' + submission.title + ']('
                                                    + submission.url + ')')
                                logger.info('Successfully messaged /u/' + moderator.name)
                            with open('../treesmodspostids.txt', 'a') as f:
                                f.write(submission.id + "\n")
            except Exception as e:
                logger.error(e)
            time.sleep(WAIT)
    
    def scanInbox(self):
        while True:
            try:
                for item in self.reddit.inbox.unread(limit=None):
                    if isinstance(item, Message):
                        if (item.subject.lower() == "agecheck"):
                            username = item.body.split()[0]
                            logger.info(item.author.name + " requested age check for " + username)
                            response = self.ageCheckUser(username)
                            logger.info(username + " underage scan complete.")
                            item.author.message("Age check results for " + username, response)
                            logger.info(item.author.name + " successfully messaged.")
                    item.mark_read()
            except Exception as e:
                logger.error(e)
            time.sleep(WAIT)
    
    def ageCheckUser(self, username):
        REGEX_STR = r"((i|I).?m (1[0-7])|eleven|twelve|.*teen)|(( |-)grader?( ?1?[0-9])?)|( ?school)|(fake id)|(can'?t buy (a )?(alcohol|papers|grinder|bong|tobacco|cig|lighter|iso|papers))"
        
        flagged = ""
        content = None
        response = ""
        itemType = None
        numProcessed = 0;
        numFlags = 0
        rteenagersflair = ""
        link = ""
        
        if (rteenagersflair != ""):
            response += "**\n/r/teenagers flair: " + rteenagersflair + "**"
        
        redditor = None
        
        try: 
            redditor = self.reddit.redditor(username)
            
            for item in redditor.new(limit=1000):
                rteenagerstagorempty = ""
                
                if (isinstance(item, Submission)):
                    content = item.title
                    if (item.is_self):
                        content = content + " || " + item.selftext
                    itemType = "Post"
                if (isinstance(item, Comment)):
                    content = item.body
                    itemType = "Comment"
                    
                if (item.subreddit.display_name == "teenagers"):
                    rteenagerstagorempty = "**(/r/teenagers)** "
                    if (rteenagersflair == "" and item.author_flair_text != None):
                        rteenagersflair = item.author_flair_text
                else:
                    rteenagerstagorempty = "(/r/" + item.subreddit.display_name + ") "
                    
                content = content.replace("\n", " ")
                if (itemType == "Post"):
                    link = "https://redd.it/" + item.id
                else:
                    link = ("https://reddit.com/r/" + item.subreddit.display_name + "/comments/" + item.link_id.split("_")[1]
                            + "/x/" + item.id)
                
                if (re.search(REGEX_STR, content)):
                    truncContent = (content[:280] + '[...]') if len(content) > 280 else content
                    flagged = flagged + ("\n|" + itemType + "|" + time.strftime('%Y-%m-%d', time.localtime(item.created_utc))
                                         + "|[**Link**](" + link + ")|" + rteenagerstagorempty + truncContent + "|")
                    numFlags += 1
                numProcessed += 1
                    
            response = response + (str(numProcessed) + " posts and comments scanned for /u/" + username + ". ")
            
        except:
            
            errorStr = "Error occurred while loading user /u/" + username
            logger.warning(errorStr)
            return errorStr
        
        if (len(response) < 1):
            response = response + ("No content found suggesting that they are underage.")
        else:
            response = response + ("The following " + str(numFlags) + " items were flagged for review:")
            if (rteenagersflair != ""):
                response = response + "\n\n**/r/teenagers flair: " + rteenagersflair + "**"
            
            response = response + "\n\n|Type|Timestamp (UTC)|Link|Content|\n|:-|:-|:-|:-|" + flagged
            
        response = (response[:10000]) if len(response) > 10000 else response
        return response
                            
                            
if __name__=="__main__":
    bot=Bot()
    bot.run()
else:
    logger.fatal('Initialization failed!')