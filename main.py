#!/usr/bin/python
import praw
import musicbrainzngs
import time
import interface
import settings
#import logging.handlers
import logging
import logger
import os
import pprint
#import psycopg2
import boto3

# The time in seconds the bot should sleep until it checks again.
SLEEP = 600


# LOGGING CONFIGURATION
LOG_FILENAME = "bot.log"
LOG_FILE_BACKUPCOUNT = 5
LOG_FILE_MAXSIZE = 1024 * 256


# LOGGING SETUP
log = logger.make_logger("bot", LOG_FILENAME, logging_level=logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)
#log = logging.getLogger("bot").setLevel(logging.INFO)
#log_formatter = logging.Formatter('%(levelname)s: %(message)s')
#log_formatter_file = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#log_stderrHandler = logging.StreamHandler()
#log_stderrHandler.setFormatter(log_formatter)
#log.addHandler(log_stderrHandler)
#if LOG_FILENAME is not None:
#	log_fileHandler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_FILE_MAXSIZE,
#	                                                       backupCount=LOG_FILE_BACKUPCOUNT)
#	log_fileHandler.setFormatter(log_formatter_file)
#	log.addHandler(log_fileHandler)
# Musicbrainz logging
#logging.getLogger("musicbrainzngs").setLevel(logging.INFO)

# MAIN PROCEDURE
def run_bot():
    
    # progmetalbot useragent and version
    app_useragent_version = os.environ['APP_USERAGENT'] + ' ' + os.environ['APP_VERSION'] + " by u/" + settings.USER_TO_MESSAGE
    # praw
    reddit = praw.Reddit(user_agent=app_useragent_version,
                         client_id=os.environ['REDDIT_CLIENT_ID'],
                         client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                         password=os.environ['REDDIT_PASSWORD'],
                         username=os.environ['REDDIT_USERNAME'])
    # musicbrainz
    musicbrainzngs.auth(os.environ['MUSICBRAINZ_USERNAME'],
                        os.environ['MUSICBRAINZ_PASSWORD'])
    musicbrainzngs.set_useragent(os.environ['APP_USERAGENT'],
                                 os.environ['APP_VERSION'],
                                 os.environ['CONTACT_EMAIL'])
    # postgresql
    #DATABASE_URL = os.environ['DATABASE_URL']
    #conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    # cloudcube AWS
    #s3 = boto3.resource('s3')
    # subreddit
    subreddit = reddit.subreddit(settings.REDDIT_SUBREDDIT)
    log.info("Starting bot \"{}\" for subreddit {}".format(app_useragent_version, settings.REDDIT_SUBREDDIT))
    log.info("Gathering posts from subreddit %s", settings.REDDIT_SUBREDDIT)
    stored_posts = interface.initialize_link_array(reddit)
    while True:
        try:
            log.info("Reading stream of submissions for subreddit %s", settings.REDDIT_SUBREDDIT)
            for submission in subreddit.stream.submissions():
                # Checks submission for accurate title/link info
                #   If submission is not from music domain, does not get checked
                # Checks submission against posts from last 6 months
                # Adds submission to list after both checks
                old_submission_id = stored_posts[0]
                if not interface.check_age_max(reddit.submission(id=old_submission_id)):
                    log.info("Purging old posts from list")
                    stored_posts = interface.purge_old_links(reddit, stored_posts)
                if interface.check_post(submission) and submission.id not in [sub.id for sub in stored_posts]:
                    #log.info("Found new post {} in subreddit {}".format(submission, settings.REDDIT_SUBREDDIT))
                    if submission.is_self:
                        post_type = "self"
                    else:
                        post_type = "link"
                    log.info("Found new {} post {} in subreddit {}".format(post_type, submission, settings.REDDIT_SUBREDDIT))
                    vars(submission)
                    bool_post = interface.check_submission(reddit, submission)
                    if bool_post:
                        interface.check_list(reddit, submission, stored_posts)
                    stored_posts.append(submission)
                
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
