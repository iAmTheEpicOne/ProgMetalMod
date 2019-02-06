#!/usr/bin/python
import praw
import musicbrainzngs
import time
import interface
import settings
import logging
import logger
import os
import pprint
#import psycopg2
import boto3
#import platform


# The time in seconds the bot should sleep until it checks again.
SLEEP = 600

# LOGGING CONFIGURATION
LOG_FILENAME = "bot.log"
LOG_FILE_BACKUPCOUNT = 5
LOG_FILE_MAXSIZE = 1024 * 256

# LOGGING SETUP
log = logger.make_logger("bot", LOG_FILENAME, logging_level=logging.DEBUG)

# MAIN PROCEDURE
def run_bot():

    # -- progmetalbot useragent and version --
    app_useragent_version = os.environ['APP_USERAGENT'] + ' ' + os.environ['APP_VERSION'] + " by u/" + settings.USER_TO_MESSAGE
    # -- praw --
    reddit = praw.Reddit(user_agent=app_useragent_version,
                         client_id=os.environ['REDDIT_CLIENT_ID'],
                         client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                         password=os.environ['REDDIT_PASSWORD'],
                         username=os.environ['REDDIT_USERNAME'])
    subreddit = reddit.subreddit(settings.REDDIT_SUBREDDIT)
    # -- musicbrainz --
    musicbrainzngs.auth(os.environ['MUSICBRAINZ_USERNAME'],
                        os.environ['MUSICBRAINZ_PASSWORD'])
    musicbrainzngs.set_useragent(os.environ['APP_USERAGENT'],
                                 os.environ['APP_VERSION'],
                                 os.environ['CONTACT_EMAIL'])
    # -- youtube --

    # -- spotify --

    # -- last.fm --

    # -- postgresql --
    #DATABASE_URL = os.environ['DATABASE_URL']
    #conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    # -- cloudcube AWS --
    #s3 = boto3.resource('s3')

    #log.info("Python platform: {}".format(platform.python_version()))
    log.info("Starting bot \"{}\" for subreddit {}".format(app_useragent_version, settings.REDDIT_SUBREDDIT))
    interface.unhide_posts(reddit)
    #log.info("Gathering posts from subreddit %s", settings.REDDIT_SUBREDDIT)
    #stored_posts = interface.initialize_link_array(reddit)
    while True:
        try:
            log.info("Reading stream of submissions for subreddit %s", settings.REDDIT_SUBREDDIT)
            for submission in subreddit.stream.submissions():
                # Checks submission for accurate title/link info
                #   If submission is not from music domain, does not get checked
                # Checks submission against posts from last 6 months
                # Adds submission to list after both checks
                if not interface.check_archived(submission) and interface.check_age_days(submission) and not interface.check_reported(submission):
                    #log.info("Found new post {} in subreddit {}".format(submission, settings.REDDIT_SUBREDDIT))
                    if interface.check_self(submission):
                        log.info("Found new self Submission: {} in Subreddit: {}".format(submission, settings.REDDIT_SUBREDDIT))
                        interface.check_selfpost(reddit, submission)
                    else:
                        log.info("Found new link Submission: {} in Subreddit: {}".format(submission, settings.REDDIT_SUBREDDIT))
                        #print(vars(submission))
                        if not interface.check_embed(submission):
                            # Link submission does not have embeded media information to use for submission checking
                            log.info("Link Submission: {} has no embedded media, will skip".format(submission))
                            continue
                        bool_post = interface.check_submission(reddit, submission)
                        if bool_post:
                            #interface.check_list(reddit, submission, stored_posts)
                            interface.check_list(reddit, submission)
                        #stored_posts.append(submission)
                        log.info("Checks complete for submission: {}".format(submission))

                # Only checks submission for accurate title/link info
                #if interface.check_post(submission):
                #    log.info("Found new post %s in subreddit %s", submission, settings.REDDIT_SUBREDDIT)
                #    interface.check_submission(reddit, submission)

            # Write stored posts to a file
            #interface.update_stored_posts(reddit, stored_posts)

        # Allows the bot to exit on ^C, all other exceptions are ignored
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error("Exception in submission stream: %s", e, exc_info=True)
            try:
                log.info("Alerting admin")
                reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalBot", "Bot had an exception {}, help!".format(e))
            except Exception as e:
                log.error("Exception in messaging admin: %s", e, exc_info=True)
        log.info("sleep for %s s", SLEEP)
        time.sleep(SLEEP)

# START BOT
if __name__ == "__main__":
    run_bot()
