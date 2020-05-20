def filterSubmissions(self):
        """
        This function is designed to supplement automoderator by removing
        submissions that match certain conditions. Currently only searches for
        submissions that seem to be asking if or how the submitter can pass a
        drug test.
        """
        DRUG_TEST_SET = {"how", "pass", "test", "?"}
        DRUG_TEST_REMOVAL_TEXT = ("Hi, /u/{0}! It looks like you are asking if "
            "(or how) you can pass a drug test. Those and other frequently "
            "asked questions are not allowed, and your post has been "
            "automatically removed.\n\nIf you believe your post was removed "
            "by mistake, please [send us a modmail](https://www.reddit.com/mes"
            "sage/compose?to=%2Fr%2F{1}&subject=about my removed post&message="
            "I'm writing to ask why my post: {2} was removed. %0D%0D)."
            )
        
        for submission in self.sub.stream.submissions(skip_existing=True):
            logger.info("Parsing post " + submission.id + " : " + submission.title[:70])
            if submission.is_self:
                # check if a submission contains *all* of the keywords in a set
                for token in DRUG_TEST_SET:
                    if (token in submission.title.lower() or
                        token in submission.selftext.lower()):
                        try:
                            submission.mod.remove()
                            submission.flair(text="removed--rule 7")
                            removal_comment = submission.reply(
                                    DRUG_TEST_REMOVAL_TEXT.format(
                                                     submission.author,
                                                     config.SUBREDDIT,
                                                     "https://redd.it/" +
                                                        submission.id))
                            removal_comment.distinguish(sticky=True)
                            logger.info("\t\\\tPOST REMOVED")
                        except:
                            logger.error("Error removing submission "
                                         + submission.id)
                            
def check420Hourly(self):
        now = datetime.utcnow()
        if (now.minute == 20):
            hrsOffset = (now.day - 20) * 24
            thisStartHour = hrsOffset + now.hour
            self.lastTz -= 1
            nowTimedelta = timedelta(hours=(hrsOffset + now.hour), minutes=now.minute) 
            livestreamsStr = ''
            with open('./res/post-template.txt', 'r') as temp:
                with open('./res/tz.csv', 'r') as tz_file:
                    tz = csv.reader(tz_file, delimiter=',')
                    for row in tz:
                        if (int(row[0]) == self.lastTz):
                            tzName = row[1]
                            tzAbbr = row[2]
                            tzDesc = row[4]
                            
                            with open('./res/livestreams.csv', 'r') as livestreams_file:
                                livestreams = csv.reader(livestreams_file, delimiter=',')
                                for stream in livestreams:
                                    streamAbsStartTime = timedelta(hours = int(stream[7]), minutes = int(stream[8]))
                                    streamAbsEndTime = timedelta(hours = int(stream[9]), minutes = int(stream[10]))
                                    streamTimeDesc = ''
                                    streamAbsStartHours = streamAbsStartTime.days * 24 + streamAbsStartTime.seconds/3600
                                    streamAbsEndHours = streamAbsEndTime.days * 24 + streamAbsEndTime.seconds/3600
                                    streamStartTimeDelta = streamAbsStartTime - nowTimedelta
                                    minsDiff = int(math.floor((streamStartTimeDelta.seconds/60) % 60))
                                    if (streamAbsStartHours > thisStartHour):
                                        hrsDiff = int(math.floor(streamStartTimeDelta.days * 24 \
                                                                 + streamStartTimeDelta.seconds/3600))
                                        streamTimeDesc = 'Starts in'
                                        if (hrsDiff > 0):
                                            streamTimeDesc = streamTimeDesc + ' ' + str(hrsDiff) + " hours"
                                        if (minsDiff > 0):
                                            streamTimeDesc = streamTimeDesc + ' ' + str(minsDiff) + " minutes"
                                    elif (streamAbsStartHours == thisStartHour):
                                        
                                        if (minsDiff <= 0):
                                            streamTimeDesc = '**Active now!**'
                                        else:
                                            streamTimeDesc = 'Starts in ' + str(minsDiff) + ' minutes' 
                                    else:
                                        if (streamAbsEndHours < thisStartHour):
                                            continue;
                                        elif (streamAbsEndHours == thisStartHour):
                                            if (minsDiff >= 0):
                                                streamTimeDesc = '**Active now!**'
                                            else:
                                                continue
                                        else:
                                            streamTimeDesc = '**Active now!**'
                                        
                                    localHrs = int(stream[7]) + int(stream[3])
                                    streamTitleAndLink = '[' + stream[0] + '](' + stream[2] + ')'
                                    streamRelStartTimeStr = str(localHrs) + ':' \
                                            + "{:02d}".format(int(stream[8])) + ' ' + stream[4] + ' (' \
                                            + streamTimeDesc + ') '
                                    livestreamsStr = livestreamsStr + "* " + streamRelStartTimeStr \
                                            + streamTitleAndLink + ': ' + stream[1] + '\n'
                            
                            body = temp.read().format(tzName=tzName, tzDesc=tzDesc, livestreamsStr=livestreamsStr)
                            title = "{tzName} Time Zone Ents: IT'S 4:20PM ON 4/20 IN THE MONTH OF 4/20!".format(tzName=tzName)
                            newPost = self.sub.submit(title, selftext=body)
                            newPost.mod.distinguish()
                            newPost.mod.sticky()
                            newPost.mod.flair(text='4:20 ' + tzAbbr + ' Celebration Post!')
                            logger.info("420 post done, self.lastTz=" + str(self.lastTz))