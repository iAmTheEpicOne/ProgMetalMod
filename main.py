#!/usr/bin/python
import praw
import time
import interface
import settings
import logging.handlers
import logging


# The time in seconds the bot should sleep until it checks again.
SLEEP = 60


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
    reddit = praw.Reddit('bot1')
    subreddit = reddit.subreddit(settings.REDDIT_SUBREDDIT)
    
    stored_links = interface.initialize_link_array(reddit)
    
    log.info("Start bot for subreddit %s", settings.REDDIT_SUBREDDIT)
    
    while True:
        try:
            for submission in subreddit.stream.submissions():
                # For each submission, check if it is younger than MAX_REMEMBER_LIMIT
                # print (interface.get_submission_age(submission).days)
                if interface.check_post(submission) and submission not in stored_links:
                    #print ("pass 1")
                    stored_links = interface.purge_old_links(stored_links) # Remove old links
                    #print ("pass 2")
                    stored_links = interface.check_list(reddit, submission, stored_links)
                    #print ("pass 3")
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
