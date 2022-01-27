import prawcore
import time
import hashlib
import datetime
import requests
from requests.utils import quote
import base64
import settings
import logging.handlers
import logging
import logger
import os
import re
import musicbrainzngs
import unicodedata
import pylast


log = logging.getLogger("bot")
# log_mb = logger.make_logger("musicbrainzngs", LOG_FILENAME, logging_level=logging.DEBUG)


def check_post(submission):
    # Return True if not archived and not self.post
    return not check_archived(submission) and not check_self(submission)


def check_archived(submission):
    # Return True if post is archived (>6 months old)
    return submission.archived


def get_submission_age(submission):
    # Returns a delta time object from the difference of the current time and the submission creation time
    current_date = datetime.datetime.utcfromtimestamp(time.time())
    submission_date = datetime.datetime.utcfromtimestamp(submission.created_utc)
    return current_date - submission_date


def check_age_max(submission):
    # Return True if age is < MAX_REMEMBER_LIMIT
    return get_submission_age(submission).days < settings.MAX_REMEMBER_LIMIT


def check_age_days(submission):
    # Return True if age is < 2 days
    return get_submission_age(submission).days < 1


def check_self(submission):
    # Return True if post is selfpost
    return submission.is_self


def check_crosspost(submission):
    # Return True if post is a crosspost
    if hasattr(submission, 'crosspost_parent_list'):
        return True
    else:
        return False


def check_approved(submission):
    # Return True if post has been approved by moderator
    # require moderator privileges
    # value is True or null
    if submission.approved is True:
        return submission.approved
    else:
        return False


def check_reported(submission):
    if hasattr(submission, 'mod_reports_dismissed'):
        for item in submission.mod_reports_dismissed:
            if item[1] == os.environ['REDDIT_USERNAME']:
                return True
    if submission.mod_reports:
        for item in submission.mod_reports:
            if item[1] == os.environ['REDDIT_USERNAME']:
                return True
    # elif submission.num_reports < 0 or submission.ignore_reports is True:
        # return True
    return False


def check_domain(domain):
    # Return True if link domain is in accepted domain list
    # Regex
    domains = re.search(r'.*(youtube.com|youtu.be|spotify.com|bandcamp.com|soundcloud.com).*', domain)
    if domains is None:
        return False
    else:
        return True


def check_embed(submission):
    # Return True if link submission has embedded info
    if submission.media is None:
        return False
    else:
        return True


def check_lazy_text_post(submission):
    # Return True if selftext contains just a link
    result = re.search(r'(?iu)^https?:\/\/\S+?$', submission.selftext)
    if result is None:
        return False
    else:
        return True


def check_album_stream(submission):
    # Returns True if url contains "album"
    domain = get_domain(submission)
    if domain in ["youtube.com", "youtu.be", "m.youtube.com"]:
        try:
            title = submission.media['oembed']['title']
        except KeyError:
            title = submission.media.oembed.title
        result = re.search(r'(?i)(full.?album|album.?stream|full.?ep|ep.?stream)', title)
        if result is None:
            result = re.search(r'(\.com\/playlist\?)', submission.url)
            if result is None:
                return False
            else:
                return True
        else:
            return True
    else:
        url = get_url(submission)
        result = re.search(r'(\.com\/album\/)', url)
        if result is None:
            return False
        else:
            return True


def check_self_promotion(submission):
    # Return True if username is in submission title for possible self-promotion
    post_title_array = get_post_title(submission)
    post_title = str(post_title_array[0])
    post_title_replace = post_title.replace(" ", "")
    user = str(submission.author)
    if user.lower() in post_title_replace.lower():
        log.info("Username: \"{}\" matches Title: \"{}\"".format(submission.author, post_title))
        return True
    else:
        return False


def check_removed(submission):
    # Returns True if submission has been removed
    # Require moderator privileges
    return submission.removed


def check_more_recent(submission_1, submission_2):
    # Returns True if submission_1 is more recent than submission_2
    age_1 = submission_1.created_utc
    age_2 = submission_2.created_utc
    return age_1 > age_2


def get_url(submission):
    # Get url
    # Regex
    url = re.search(r'(?:youtube\.com.*?=|youtu\.be\/)(.{11})', submission.url)
    if url is None:
        return submission.url
    else:
        return url.group(1)


def get_musicbrainz_result(artist, song):
    # Checks artist and song info against musicbrainz database
    # Currently only returns True or False value
    result = musicbrainzngs.search_recordings(artist=artist, recording=song)
    # If the artist and song matches a recording in database then return True
    # if not result['recording-list']:
    return result


def get_lastfm_result(artist, song):
    lastfm = pylast.LastFMNetwork(api_key=os.environ['LASTFM_KEY'],
                                  api_secret=os.environ['LASTFM_SECRET'])
    results = pylast.TrackSearch(artist, song, lastfm)
    results = results.get_next_page()
    return results


def get_domain(submission):
    return submission.domain


def get_unicode_normalized(word):
    try:
        word.encode('utf-8', 'ignore').decode('ascii')
    except UnicodeDecodeError:
        normalized = unicodedata.normalize('NFD', word)
        new_word = u"".join([c for c in normalized if not unicodedata.combining(c)])
        return new_word
    else:
        return word


def get_spotify_authorization():
    print("getting spotify authorization")
    clientID = os.environ['SPOTIFY_ID']
    clientSecret = os.environ['SPOTIFY_SECRET']
    authorization = "Basic " + base64.b64encode(bytes(clientID+':'+clientSecret, 'utf-8')).decode()

    payload = {'grant_type': 'client_credentials'}
    headers = {'Authorization': authorization}

    r = requests.post('https://accounts.spotify.com/api/token', data=payload, headers=headers)
    rJson = r.json()
    print(rJson)
    accessToken = rJson["access_token"]
    accessTokenAuthorization = "Bearer " + accessToken

    return accessTokenAuthorization


def get_spotify_track_from_link(trackLink):
    authorization = get_spotify_authorization()

    trackId = re.search(r'(?i)https?:\/\/open.spotify.com/track/([a-z0-9]{22})', trackLink).group(1)

    url = 'https://api.spotify.com/v1/tracks/' + trackId
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json',
               'Authorization': authorization}

    r = requests.get(url, headers=headers)
    rJson = r.json()
    # print(rJson)


def get_spotify_track_from_title(artist, track):
    authorization = get_spotify_authorization

    url = 'https://api.spotify.com/v1/search?q=track:"' + quote(track) + '"+artist:"' + quote(artist) + '"&type=track'
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json',
               'Authorization': authorization}

    r = requests.get(url, headers=headers)
    rJson = r.json()
    print(rJson)


def get_spotify_album_from_link(albumLink):
    authorization = get_spotify_authorization()

    albumID = re.search(r'(?i)https?:\/\/open.spotify.com/album/([a-z0-9]{22})', albumLink).group(1)

    url = 'https://api.spotify.com/v1/albums/' + albumID
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json',
               'Authorization': authorization}

    r = requests.get(url, headers=headers)
    rJson = r.json()
    # print(rJson)

    return rJson


def get_spotify_album(artist, album):
    authorization = get_spotify_authorization()

    url = 'https://api.spotify.com/v1/search?q=album:"' + quote(album) + '"+artist:"' + quote(artist) + '"&type=album'
    headers = {'Accept': 'application/json',
               'Content-Type': 'application/json',
               'Authorization': authorization}

    r = requests.get(url, headers=headers)
    rJson = r.json()
    print(rJson)

    # albumNum = rJson["albums"]["total"]
    # albums = rJson["albums"]["items"]
    # artist = albums[0]


def get_spotify_artist_from_id(artistId):
    authorization = get_spotify_authorization()
    url = 'https://api.spotify.com/v1/artists/' + artistId


def get_link_title(reddit, submission):
    # Get 'Artist' and 'Song' from the embedded link info
    # Returns [artist, song] or 'None' if soundcloud link (for now)
    # Note that artist=None if auto-generated YouTube channel "Various Artist - Topic"
    # None that song=None and artist=link_title if YouTube video title didn't match regex
    #   link_title can then be used as crosscheck with reddit post title info
    domain = get_domain(submission)
    if domain == "spotify.com":
        try:
            description = submission.media['oembed']['description']
        except KeyError:
            description = submission.media.oembed.description
        # Regex
        title = re.search('(.*), a song by (.*) on Spotify', description)
        song = title.group(1)
        artist = title.group(2)
        link_title = [artist, song]
    elif domain == "bandcamp.com":
        try:
            description = submission.media['oembed']['title']
        except KeyError:
            description = submission.media.oembed.title
        # Regex
        title = re.search('(.*), by (.*)', description)
        song = title.group(1)
        artist = title.group(2)
        link_title = [artist, song]
    elif domain in ["youtube.com", "youtu.be", "m.youtube.com"]:
        # Need to add YouTube API for better info
        # Currently cannot access a video's description
        try:
            link_author = submission.media['oembed']['author_name']
            link_media_title = submission.media['oembed']['title']
        except KeyError:
            link_author = submission.media.oembed.author_name
            link_media_title = submission.media.oembed.title
        if " - Topic" in link_author:
            # YouTube channel is auto-generated "Artist - Topic"
            # so video title is the song name
            song = link_media_title
            if "Various Artists" in link_author:
                # YouTube channel is "Various Artist - Topic"
                # so artist name is unknown
                # need to use YouTube api to access video description to get correct artist name
                artist = None
            else:
                # Regex
                topic = re.search('(.*) - Topic', link_author)
                artist = topic.group(1)
            link_title = [artist, song]
        # If video is normal upload by label or user
        else:
            # Regex
            # title = re.search(r'(?iu)^(.*?)\s?(?:-{1,2}|\u2014|\u2013)\s?(?:"|)(\(?[^"]*?)\s?(?:["].*|(?:\(|\[|{).*[^)]$|[-([].*?(?:full|video|instrumental|review|album|official|premiere?|lyric|playthrough|single|cover|[0-9]{4}).*|$|\n)', link_media_title)
            title = re.search(r'(?iu)^(.*\S-\S.*|.+?)\s?(?:-{1,2}|\u2014|\u2013|\s(?=["“”]))\s?(?:["“”]|)(\(?[^“"”]*?)\s?(?:["“”].*|\s(?:\(|\[|{).*[^)]$|[-(["“”].*?(?:full|audio|video|instrumental|review|album|official|premiere?|lyric|playthrough|single|cover|version|live|music|[0-9]{4}).*|$|\n)', link_media_title)
            if title is None:
                link_title = [link_media_title, None]
            else:
                artist = title.group(1)
                song = title.group(2)
                link_title = [artist, song]
    elif domain == "soundcloud.com":
        # Need to add SoundCloud API for info
        link_title = None
    else:
        link_title = None
    if link_title is not None:
        if link_title[0] is not None:
            link_title[0] = get_unicode_normalized(link_title[0])
        if link_title[1] is not None:
            link_title[1] = get_unicode_normalized(link_title[1])
    return link_title


def get_post_title(submission):
    # REGEX OVERLOAD INCOMING
    # Use regex string in ' ' on regexr.com and check out all the titles it catches!
    # re.search will store 'Artist' in title.group(1) and 'Song' in title.group(2)
    # title = re.search(r'(?iu)(?:(?:^[()[\]{}|].*?[()[\]{}|][\s|\W]*)|(?:^))(.*?)\s?(?:-{1,2}|\u2014|\u2013)\s?(?:"|)(\(?[^"]*?)\s?(?:\/\/.*|\\\\.*|\|\|.*|\|.*\||["].*|(?:\(|\[|{).*[^)]$|[-([|:;].*?(?:favorite|video|full|tour|premiere?|released|cover|album|drum|guitar|bass|vox|vocal|voice|playthrough|ffo|official|new|metal|prog|test\spost).*|$|\n)', submission.title)
    title = re.search(r'(?iu)(?:(?:^[()[\]{}|].*?[()[\]{}|][\s|\W]*)|(?:^))([^([]*\S-\S[^([]*|[^([]*?)\s?(?:-{1,2}|\u2014|\u2013|\s(?=[“"”]))\s?(?:[“"”]|)([^“"”]*?)\s?(?:\/\/.*|\\\\.*|\|\|.*|\|.*\||[“"”].*|\s(?:[([{]).*[^)\]}]$|(?:[-([|;“"”]|:\s).*?(?:favorite|audio|video|full|tour|live|premiere?|released|cover|version|music|album|drum|guitar|bass|vox|vocal|voice|playthrough|ffo|for fans of|official|new|metal|prog|recommend|[0-9]{4}).*|$|\n)', submission.title)
    if title is None:
        # ah fuck it didn't work
        post_title = [get_unicode_normalized(submission.title), None]
    else:
        artist = get_unicode_normalized(title.group(1))
        song = get_unicode_normalized(title.group(2))
        post_title = [artist, song]
    return post_title


def get_reddit_search_listing(reddit, context, query_text):
    # Search for query in last year of submissions where context is url or title
    # Returns listing object of submission ordered new -> old
    search_query = context + ":" + query_text
    listing = reddit.subreddit(settings.REDDIT_SUBREDDIT).search(search_query, sort='new', time_filter='year', limit=10)
    return listing


def report_musicbrainz(reddit, submission):
    # Musicbrainz query was unsuccessful
    # Submission will be reported and message sent to mods
    log.info("Song not found in Musicbrainz: Reporting {}".format(submission.shortlink))
    submission.report("Not Found in Musicbrainz")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalMod: Not Found in Musicbrainz", "Please look at [this post]({}) for failed Musicbrainz result or check the modmail.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    # reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalMod: Not Found in Musicbrainz", "Please look at [this post]({}) for failed Musicbrainz result.\n\nIf you have a question please message u/{}".format(submission.shortlink, settings.USER_TO_MESSAGE))


def rule_bad_title(reddit, submission):
    # Submission was found to have an incorrect title
    # Submission will be reported and message sent to mods
    log.info("Rule Violation (Bad Title): Reporting {}".format(submission.shortlink))
    # submission.mod.remove()
    submission.report("Bad Title Format")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalMod: Bad Title Format", "Please look at [this post]({}) to check for proper title format.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    # reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalMod: Bad Title Format", "Please look at [this post]({}) and check for a proper title format.\n\nIf you have a question please message u/{}".format(submission.shortlink, settings.USER_TO_MESSAGE))


def rule_bad_title_report(reddit, submission):
    # Submission was found to possibly have an incorrect title
    # Submission will be reported to mods for verification
    log.info("Possible Rule Violation (Bad Title): Reporting {}".format(submission.shortlink))
    submission.report("Possible Bad Title/Link Match")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalMod: Bad Title/Link Match", "Please look at [this post]({}) to check for proper match of submission title and linked song.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    # reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalMod: Bad Title/Link Match", "Please look at [this post]({}) to check for a proper match of submission title and linked song.\n\nIf you have a question please message u/{}".format(submission.shortlink, settings.USER_TO_MESSAGE))


def rule_six_month(reddit, submission, sub):
    # Submission was found to violate the 'repost in six months' rule
    # Submission will be reported and message sent to mods
    log.info("Rule Violation (6-month Repost): Reporting {}, repost of {}".format(submission.shortlink, sub.shortlink))
    # submission.mod.remove()
    submission.report("Repost of {}".format(sub.shortlink))
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalMod: Song Repost", "Please look at [this post]({}) for a possible repost of [this post]({}).".format(submission.shortlink, sub.shortlink))
    # ***UNCOMMENT LATER***
    # reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalMod: Song Repost", "Please look at [this post]({}) for a possible repost of [this post]({}).\n\nIf you have a question please message u/{}".format(submission.shortlink, sub.shortlink, settings.USER_TO_MESSAGE))


def rule_album_stream(reddit, submission):
    # Submission was found to link to a full album stream on bandcamp, spotify, or youtube
    # Submission will be reported and message sent to mods
    log.info("Rule Violation (Album Stream): Reporting {}".format(submission.shortlink))
    # submission.mod.remove()
    submission.report("Full Album Stream")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalMod: Full Album Stream", "Please look at [this post]({}) which may violate the full album stream rule.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    # reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalMod: Full Album Stream", "Please look at [this post]({}) which may violate the full album stream rule.\n\nIf you have a question please message u/{}".format(submission.shortlink, settings.USER_TO_MESSAGE))


def rule_self_promotion(reddit, submission):
    # Submission was found to possibly be self-promotion
    # Submission will be reported and message sent to mods
    log.info("Rule Violation (Self-Promotion): Reporting {}".format(submission.shortlink))
    submission.report("Possible Self-Promotion")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalMod: Possible Self-Promotion", "Please look at [this post]({}) for possible self-promotion because the user's name matches the artist's name.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    # reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalMod: Possible Self-Promotion", "Please look at [this post]({}) for possible self-promotion because the user's name matches the artist's name.\n\nIf you have a question please message u/{}".format(subission.shortlink, settings.USER_TO_MESSAGE))


def rule_lazy_selfpost(reddit, submission):
    # submission was found to be a self post with only a link
    # Submission will be reported and message sent to mods
    log.info("Rule Violation (Low-effort Selfpost): Reporting {}".format(submission.shortlink))
    submission.report("Link as Selfpost")
    reddit.redditor(settings.USER_TO_MESSAGE).message("ProgMetalMod: Link as Selfpost", "Please look at [this post]({}) for a lazy selfpost containing just a link.".format(submission.shortlink))
    # ***UNCOMMENT LATER***
    # reddit.subreddit(settings.REDDIT_SUBREDDIT).message("ProgMetalMod: Link as Selfpost", "Please look at [this post]({}) for a lazy selfpost containing just a link.\n\nIf you have a question please message u/{}".format(subission.shortlink, settings.USER_TO_MESSAGE))


def rule_violation(rules_violated, rule):
    # Appends a rule to rules_violated for specific submission
    rules_violated += [rule]
    return rules_violated


def perform_mod_actions(reddit, rules_violated):
    # For each rule in rules_violated, perform mod actions
    if len(rules_violated) > 1:
        submission = rules_violated[0]
        for rule in rules_violated[1:]:
            if rule == 1:
                # bad title
                rule_bad_title(reddit, submission)
            elif 2 in rule:
                # possible bad title - report only
                rule_bad_title_report(reddit, submission)
            elif 3 in rule:
                # six month repost
                rule_six_month(reddit, submission, rule[1])


def unhide_posts(reddit):
    unhidden_count = 0
    while True:
        posts = [post for post in reddit.user.me().hidden(limit=40)]
        if not posts:
            log.info("{} posts have been unhidden.".format(unhidden_count))
            break
        posts[0].unhide(other_submissions=posts[1:40])
        unhidden_count += 1


def initialize_link_array(reddit):
    # Initializes the link array of all past submissions
    # No need to check about removing older posts, since we do that before checking in the main loop anyway
    if 'stored_posts' not in locals():
        stored_posts = []
    # else:
    #    with open("stored_posts.txt", "r") as f:
    #        stored_posts = f.read()
    #        stored_posts = stored_posts.split("\n")
    #        stored_posts = list(filter(None, stored_posts))
    total_posts = 0
    stored_count = 0
    # Reddit API only allows up to 1000 posts in listings
    for submission in reddit.subreddit(settings.REDDIT_SUBREDDIT).new(limit=None):
        total_posts += 1
        if check_post(submission) and not check_age_days(submission):
            # if submission.url not in [sub.url for sub in stored_posts] or submission not in stored_posts:
            if submission.id not in [sub.id for sub in stored_posts]:
                stored_posts.append(submission)
                stored_count += 1
    last_submission = stored_posts[stored_count - 1]
    last_name = last_submission.name
    current_time = int(time.time())
    earliest_time = current_time - 86400*181
    # while stored_posts[stored_count-1].created_utc > earliest_time:
    for submission in reddit.subreddit(settings.REDDIT_SUBREDDIT).new(limit=None, params={"after": "{}".format(last_name)}):
        total_posts += 1
        if check_post(submission) and not check_age_days(submission):
            if submission.id not in [sub.id for sub in stored_posts]:
                stored_posts.append(submission)
                stored_count += 1
            if submission.created_utc < earliest_time:
                break
    # reverse so oldest are first
    stored_posts.reverse()
    stored_posts = list(filter(None, stored_posts))
    # log.info("Searched a total of {} posts".format(total_posts))
    log.info("Found {} posts within last six months".format(stored_count))
    # log.info("Stored posts array has size {} after filter".format(len(stored_posts)))
    # stored_ids = []
    # for sub in stored_posts:
    #    stored_ids.append(sub.id)
    # print(', '.join(stored_ids))
    return stored_posts

# postgresql create table
# def create_table():
#    postgresql create table
#    commands = (
#        """
#        CREATE TABLE posts (
#            post_id SERIAL PRIMARY KEY
#        """)


def update_stored_posts(reddit, stored_posts):
    with open("stored_posts.txt", "w") as f:
        for submission in stored_posts:
            f.write(submission.id + "\n")


def merge_crosspost_parent(reddit, submission):
    # Merge media information from parent into crosspost
    if hasattr(submission, 'crosspost_parent_list'):
        parentName = submission.crosspost_parent
        parentId = parentName[3:]
        parent = reddit.submission(id=parentId)
        submission.media = parent.media
    return submission


def check_selfpost(reddit, submission):
    # Check a self.subreddit submission
    if check_lazy_text_post(submission):
        rule_lazy_selfpost(reddit, submission)


def check_submission(reddit, submission):
    # Check the submission and link information for album stream, self-promotion, and bad title formatting
    # Artist and Song name verification happens here with checks against submission title
    link_domain = get_domain(submission)
    if not check_domain(link_domain):
        # link domain is not youtube, spotify, bandcamp, or soundcloud
        # could check domain against secondary list including facebook, twitter, metal magazines, etc. for different handling
        log.info("Link submission to {}".format(link_domain))
        # Submission will not be cross-checked with list
        return False
    if check_album_stream(submission):
        # does not include spotify playlists as album streams
        log.info("Submission {} is an album stream".format(submission.id))
        rule_album_stream(reddit, submission)
        # Submission will not be cross-checked with list
        return False
    # rules_violated = []
    post_title = submission.title
    post_info = get_post_title(submission)
    if post_info[1] is None:
        # Report submission for bad title rule violation
        # Could do second regex check for "Song by Artist"
        rule_bad_title(reddit, submission)
        # Submission will not be cross-checked with list
        return False
    else:
        post_artist = post_info[0]
        post_song = post_info[1]
    if check_self_promotion(submission):
        rule_self_promotion(reddit, submission)
        # Currently keeps checking the post for other violations.
        #   No proper way to consolidate rule violations into one report method
        #   It's possible that the self-promotion report will be overwritten with another report during check
    link_info = get_link_title(reddit, submission)
    if link_info is None:
        # None means soundcloud link which is not handled yet
        # currently: do nothing
        pass
    else:
        reportBadTitle = False
        noLinkArtist = False
        noLinkSong = False
        link_artist = link_info[0]
        link_song = link_info[1]
        if link_artist is not None:
            link_artist_lower = link_artist.lower()
        if link_song is not None:
            link_song_lower = link_song.lower()
        post_artist_lower = post_artist.lower()
        post_song_lower = post_song.lower()
        if link_artist is None:
            # auto-generated YouTube channel "Various Artist - Topic"
            # artist unknown until YouTube API enabled, song is known
            noLinkArtist = True
            if link_song_lower not in post_song_lower or post_song_lower not in link_song_lower:
                # Report submission for link info not matching post info
                text = "Song: \"{}\" does not match Linked Song: \"{}\""
                vars = [post_song, link_song]
                reportBadTitle = True
        elif link_song is None:
            # YouTube video title didn't match regex, so link_artist is full video title
            # Can check post_info against this info
            noLinkSong = True
            video_title = link_artist
            if post_artist_lower not in video_title.lower() or post_song_lower not in video_title.lower():
                # Report submission for artist or song in post title not found in link title
                text = "Artist: \"{}\" or Song: \"{}\" does not match Title: \"{}\""
                vars = [post_artist, post_song, video_title]
                reportBadTitle = True
        elif post_artist_lower not in link_artist_lower and link_artist_lower not in post_artist_lower:
            try:
                link_title = submission.media['oembed']['title']
            except KeyError:
                link_title = submission.media.oembed.title
            if post_artist_lower not in link_title.lower():
                # Report submission for artist or song in post title not found in link title
                text = "Artist: \"{}\" or Song: \"{}\" does not match Title: \"{} -- {}\""
                vars = [post_artist, post_song, link_artist, link_song]
                reportBadTitle = True
        elif post_song_lower not in link_song_lower and link_song_lower not in post_song_lower:
            try:
                link_title = submission.media['oembed']['title']
            except KeyError:
                link_title = submission.media.oembed.title
            if post_song_lower not in link_title.lower():
                # Report submission for artist or song in post title not found in link title
                text = "Artist: \"{}\" or Song: \"{}\" does not match Title: \"{} -- {}\""
                vars = [post_artist, post_song, link_artist, link_song]
                reportBadTitle = True
        if reportBadTitle:
            # Title is potentially bad, confirm with typo-correction
            # Get results from last.fm to compare
            lastfmResults = get_lastfm_result(post_artist, post_song)
            for result in lastfmResults:
                # Check against search results for possible typo in title
                # Typos in title will not be reported
                title = re.search(r'(?iu)^(.*?)\s-\s(.*$)', str(result))
                artist = title.group(1)
                song = title.group(2)
                artist_lower = artist.lower()
                song_lower = song.lower()
                if noLinkArtist:
                    if song_lower in link_song_lower or link_song_lower in song_lower:
                        reportBadTitle = False
                elif noLinkSong:
                    video_title_lower = link_artist.lower()
                    if artist_lower in video_title_lower and song_lower in video_title_lower:
                        reportBadTitle = False
                else:
                    if artist_lower in link_artist_lower and song_lower in link_song_lower:
                        reportBadTitle = False
                    elif link_artist_lower in artist_lower and link_song_lower in song_lower:
                        reportBadTitle = False
                    if not reportBadTitle:
                        break
    if reportBadTitle:
        log.info(text.format(*vars))
        rule_bad_title_report(reddit, submission)
    # mb_result = get_musicbrainz_result(post_artist, post_song)
    # count = mb_result['recording-count']
    # if count < 1:
    #    report_musicbrainz(reddit, submission)
    # can check for correct listing within musicbrainz result
    # else:
    #    print(mb_result)
    log.info("Domain: {:14} Song submitted: {} - {}".format(link_domain, post_artist, post_song))
    # Submission will be cross-checked with list
    return True


# def check_list(reddit, submission, stored_posts):
def check_list(reddit, submission):
    # Cross-check submission against list for matching url or title info
    # If matched, report post
    # If not, add it to the list
    # Check if exact url already exists
    post_url = get_url(submission)
    post_title_split = get_post_title(submission)
    if post_title_split[1] is None:
        post_title = post_title_split[0]
        title_query = "'" + post_title_split[0] + "'"
    else:
        post_title = post_title_split[0] + " -- " + post_title_split[1]
        title_query = "'" + post_title_split[0] + "' '" + post_title_split[1] + "'"
    # log.info("Cross-checking Url: \"{}\" and Title: \"{}\" with older posts".format(post_url, post_title))
    # POSSIBILITY OF REVERSE TITLE LIKE *SONG - ARTIST*
    # Method is probably neutered because failed get_post_title() will not match "artist -- song"
    # for old_submission in stored_posts:
        # CHECK IF OLD SUBMISSION HAS BEEN REMOVED
    #    old_post_url = get_url(old_submission)
    #    if post_url in old_post_url:
    #        log.info("Url match of \"{}\" and \"{}\"".format(post_url, old_post_url))
    #        rule_six_month(reddit, submission, old_submission)
    #        break
    #    else:
    #        old_post_title_split = get_post_title(old_submission)
    #        if old_post_title_split[1] is None:
    #            old_post_title = old_post_title_split[0]
    #        else:
    #            old_post_title = old_post_title_split[0] + " -- " + old_post_title_split[1]
    #        check both ways incase one title has extra (descriptors) that weren't caught in get_post_title()
    #        if post_title.lower() in old_post_title.lower() or old_post_title.lower() in post_title.lower():
    #            log.info("Title match of \"{}\" and \"{}\"".format(post_title, old_post_title))
    #            rule_six_month(reddit, submission, old_submission)
    #            break
    # Compare submission to search results
    # Only happens if previous stored_posts check found no match
    # May prioritize a reddit search before list check if it's efficient
    log.info("Searching for Url: \"{}\" and Title: \"{}\" in subreddit".format(post_url, post_title))
    post_title_lower = post_title.replace(" -- ", " ").lower()
    try:
        query = post_url
        context = "url"
        search_listing = get_reddit_search_listing(reddit, context, query)
        for search_result in search_listing:
            if not check_archived(search_result) and search_result.id is not submission.id and check_more_recent(submission, search_result):
                result_url = get_url(search_result)
                if result_url is post_url:
                    log.info("Url match of \"{}\" and \"{}\"".format(post_url, result_url))
                    rule_six_month(reddit, submission, search_result)
                    break
        search_listing = None
        # try search by removing possible "(extra info)" info from the title with regex
        context = "title"
        search_listing = get_reddit_search_listing(reddit, context, title_query)
        for search_result in search_listing:
            # extraneous request to fix lazy object
            result_url = get_url(search_result)
            if submission.id not in search_result.id:
                if not check_archived(search_result) and check_more_recent(submission, search_result):
                    result_title_split = get_post_title(search_result)
                    if result_title_split[1] is None:
                        result_title = result_title_split[0]
                    else:
                        result_title = result_title_split[0] + " -- " + result_title_split[1]
                    log.info("Comparing to Post: {} with Title: \"{}\"".format(search_result.id, result_title))
                    result_title_lower = result_title.replace(" -- ", " ").lower()
                    # check both ways incase one title has extra (descriptors) that weren't caught in get_post_title()
                    if post_title_lower in result_title_lower or result_title_lower in post_title_lower:
                        log.info("Title match of \"{}\" and \"{}\"".format(post_title, result_title))
                        rule_six_month(reddit, submission, search_result)
                        break
    except prawcore.exceptions.ServerError as e:
        # HTTP Exception, will skip current search
        # e._raw.status_code will show 503, etc.
        log.error("Exception in reddit search: %s", e, exc_info=True)


def purge_old_links(reddit, stored_posts):
    # Removes links archived and removed posts from queue
    for submission in stored_posts:
        # check_removed is unused at the moment until mod privileges
        # if check_archived(submission) or check_removed(submission):
        if check_archived(submission):
            stored_posts.remove(submission)
        else:
            break
    stored_posts = list(filter(None, stored_posts))
    return stored_posts


def check_url(url):
    response = requests.get(url)
    m = hashlib.md5()
    # print response.text[0:1024]
    m.update(response.text.encode("utf-8"))
    return m.digest()


def log_info(submission):
    domain = get_domain(submission)
    title = get_post_title(submission)
    # possibly format title with .title() or capwords()
    if title[1] is None:
        title_str = title[0]
    else:
        title_str = title[0] + " -- " + title[1]
    log.info("Link: {}  Domain: {:14}  Title: {}".format(submission, domain, title_str))
