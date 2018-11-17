import os
import re
import sys
import praw
import time
import calendar
import datetime
import logging
from praw.models.reddit.subreddit import SubredditModeration

sys.path.append(os.path.abspath('..'))
import config

# consts
WAIT = 60 # waiting time between update passes (in seconds)

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
    subr = reddit.subreddit(config.SUBREDDIT)

    def __init__(self):
        # print(subr.mod.settings())
        self.curDay = datetime.datetime.now().isoweekday()
        logfile_name_format = datetime.datetime.now().strftime("log_%Y-%m-%d")
        
        # Set up logging
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('../logfiles/' + logfile_name_format + '.txt')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(LOG_FORMAT)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(LOG_FORMAT)
        logger.addHandler(fh)
        logger.addHandler(ch)
        logger.info("Bot initialized for /r/" + config.SUBREDDIT + " as /u/"
                    + config.USERNAME)

    def run(self):
        while True:
            logger.debug("begin scheduled tasks")
            newDay = datetime.datetime.now().isoweekday()
            if newDay != self.curDay:
                self.dayChange(newDay)
            logger.debug("end scheduled tasks")
            time.sleep(WAIT)
        self.update()
        logger.info('log hit run')
        print('hit run()')
        
    def dayChange(self, newDay):
        """
        This function activates and de-activates the /r/trees
        weekend stylesheet. It finds a specified block of code, and
        either inserts or removes CSS comment markers based on the day
        of the week.
        """
        css = self.subr.stylesheet.__call__().stylesheet
        curTime = datetime.datetime.now().strftime(
                "%b %d %Y %H:%M:%S EST (UTC-5)")
        
        if newDay == 1:  # MONDAY
            SubredditModeration(self.subr).update(link_type = 'any')
            css = re.sub(r'\*  BEGIN AUTOMATIC UPDATE AREA\n \*/\n\n',
                         '*  BEGIN AUTOMATIC UPDATE AREA\n */\n/*\n', css)
            css = re.sub(r'\n/\*\n \*  END AUTOMATIC UPDATE AREA',
                         '*/\n/*\n *  END AUTOMATIC UPDATE AREA', css)
        
        if newDay == 6:  # SATURDAY
            css = re.sub(r'\*  BEGIN AUTOMATIC UPDATE AREA\n \*\/\n\/\*\n',
                         '*  BEGIN AUTOMATIC UPDATE AREA\n */\n\n', css)
            css = re.sub(r'%%sunday%%', '%%saturday%%', css)
            css = re.sub(r'\*\/\n\/\*\n \*  END AUTOMATIC UPDATE AREA',
                         '\n/*\n *  END AUTOMATIC UPDATE AREA', css)
            
        if newDay == 7:  # SUNDAY
            css = re.sub(r'%%saturday%%', '%%sunday%%', css)
            SubredditModeration(self.subr).update(link_type = 'self')
        
        if newDay in (1, 6, 7):
            newCSS = re.sub(r'  last change:.*.\n', '  last change: ' + curTime
                            + '\n', css)
            self.subr.stylesheet.update(newCSS,
                                        'scheduled stylesheet update for '
                                        + calendar.day_name[newDay])
            logger.info("Stylesheet successfully updated.")
    
        self.curDay = newDay
        self.logfile_name_format = datetime.datetime.now().strftime(
                "log_%Y-%m-%d")
        self.fh = logging.FileHandler('../logfiles/' + self.logfile_name_format
                                      + '.txt')
        
    def update(self):
        logger.info('log hit update')

if __name__=="__main__":
    bot=Bot()
    bot.run()
else:
    logger.fatal('Initialization failed!')