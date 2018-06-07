#!/usr/bin/python
import praw
import time
import interface
import settings
import logging.handlers
import logging
import os
import pprint


# The time in seconds the bot should sleep until it checks again.
SLEEP = 600


# LOGGING CONFIGURATION
LOG_LEVEL = logging.INFO
LOG_FILENAME = "bot.log"
LOG_FILE_BACKUPCOUNT = 5
LOG_FILE_MAXSIZE = 1024 * 256


# LOGGING SETUP
log = logging.getLogger("bot")
log.setLevel(LOG_LEVEL)
log_formatter = logging.Formatter('%(levelname)s: %(message)s')
log_formatter_file = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_stderrHandler = logging.StreamHandler()
log_stderrHandler.setFormatter(log_formatter)
log.addHandler(log_stderrHandler)
if LOG_FILENAME is not None:
	log_fileHandler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_FILE_MAXSIZE,
	                                                       backupCount=LOG_FILE_BACKUPCOUNT)
	log_fileHandler.setFormatter(log_formatter_file)
	log.addHandler(log_fileHandler)
	

# MAIN PROCEDURE
def run_bot():
    reddit = praw.Reddit(user_agent='ProgMetalBot 0.1',
                         client_id=os.environ['REDDIT_CLIENT_ID'],
                         client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                         password=os.environ['REDDIT_PASSWORD'],
                         username=os.environ['REDDIT_USERNAME'])
                         
    subreddit = reddit.subreddit(settings.REDDIT_SUBREDDIT)
    
    log.info("Gathering posts from subreddit %s", settings.REDDIT_SUBREDDIT)
    stored_posts = interface.initialize_link_array(reddit)
    
    log.info("Start bot for subreddit %s", settings.REDDIT_SUBREDDIT)
    while True:
        try:
            log.info("Reading stream of submissions for subreddit %s", settings.REDDIT_SUBREDDIT)
            for submission in subreddit.stream.submissions():
                # For each submission, check if it is younger than MAX_REMEMBER_LIMIT
                #print(submission.title) # to make it non-lazy
                #pprint.pprint(vars(submission))
                #break
                if interface.check_post(submission) and submission not in stored_posts:
                    # Remove links > MAX_REMEMBER_LIMIT
                    log.info("Found new post in subreddit %s", settings.REDDIT_SUBREDDIT)
                    stored_posts = interface.purge_old_links(stored_posts)
                    stored_posts = interface.check_list(reddit, submission, stored_posts)
            
            # Write stored posts to a file
            #interface.update_stored_posts(stored_posts)

        # Allows the bot to exit on ^C, all other exceptions are ignored
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error("Exception %s", e, exc_info=True)

        log.info("sleep for %s s", SLEEP)
        time.sleep(SLEEP)


# START BOT
if __name__ == "__main__":
    run_bot()
