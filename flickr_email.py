#! /usr/bin/python3

import argparse
import glob
import configparser
import time
import os
import os.path
import shutil
import smtplib
from email.mime.text import MIMEText
from email import charset
import hashlib
import json
import urllib.request
import pprint

import flickr_api
import jinja2


def write_state(state):
    shutil.copy('state.ini', 'state.bak')
    with open('state.ini', 'w') as state_file:
    	state.write(state_file)

def get_state_array(state, section, option):
    value = state.get(section, option)
    if value:
        return value.split(',')
    else:
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Send email when new pictures are posted to Flickr.')

    parser.add_argument('--user_add_interactive', '-i', action='store_true',
                        help='add a user interactively based on OAuth')
    parser.add_argument('--user_add', '-a', action='store_true',
                        help='prepare adding a user based on OAuth')
    parser.add_argument('--user_auth_verifier', '-b', action='store',
                        help='finish adding the user based on OAuth')
    parser.add_argument('--user_old_auth', '-o', action='store',
                        help='add a user based on a pre-OAuth token')
    parser.add_argument('--user_delete', '-d', action='store', help='remove a user')
    parser.add_argument('--since_days', '-s', action='store', type=int,
                        help='override default period (last execution or 1 day)')
    parser.add_argument('--quiet', '-q', action='store_true', help='no output for normal operation')
    parser.add_argument('--verbose', '-v', action='store_true', help='print extra data')
    parser.add_argument('--dry_run', '-n', action='store_true', help='don\'t send email')
    parser.add_argument('--smtp_debug', action='store_true', help='print smtp debug messages')

    args = parser.parse_args()

    state = configparser.RawConfigParser({
        'last_date': int(time.time() - 24 * 60 * 60),
        'smtp_from': 'admin@example.com',
        'smtp_to': 'clients@example.com',
        'smtp_cc': '',
        'smtp_bcc': '',
        'smtp_subject': 'New photos',
        'smtp_port': 25,
        'smtp_server': 'localhost',
        'smtp_tls': 'false',
    })
    state.add_section('main')
    state.read("state.ini")

    if args.since_days:
        # noinspection PyTypeChecker
        state.set('main', 'last_date', int(time.time() - args.since_days * 24 * 60 * 60))

    # set up flickr_api app credentials
    try:
        flickr_api.set_keys(api_key=state.get('main', 'api_key'),
                            api_secret=state.get('main', 'api_secret'))
    except configparser.NoOptionError:
        state.set('main', 'api_key', 'API_KEY')
        state.set('main', 'api_secret', 'API_SECRET')
        write_state(state)
        exit("Please fill in the api_key and api_secret in state.ini")

    if args.user_add_interactive:
        a = flickr_api.auth.AuthHandler()
        print("Open this URL in a web browser and authorize", a.get_authorization_url("read"))

        oauth_token = raw_input("Paste the oauth_verifier parameter here: ")

        a.set_verifier(oauth_token)
        flickr_api.set_auth_handler(a)

        user = flickr_api.test.login()
        print("Authorized user:", user)

        if not os.path.exists('users'):
            os.mkdir('users')
        a.save("users/" + user.username)
        return

    if args.user_add:
        a = flickr_api.auth.AuthHandler()
        print("Open this URL in a web browser and authorize", a.get_authorization_url("read"))
        print("Then run the command again with --user_auth_verifier <oauth_verifier> "
              "to finish authorizing")

        if not os.path.exists('tmp_users'):
            os.mkdir('tmp_users')

        # can't use a.save() because that method requires an access_token
        # and all we have is a request_token
        with open("tmp_users/" + a.request_token.key, "w") as f:
            f.write("\n".join([a.request_token.key,
                               a.request_token.secret]))
        return

    if args.user_auth_verifier:
        # we don't know which of the temp users matches the verifier, try each of them in turn
        for f in glob.glob("tmp_users/*"):
            try:
                with open(f, "r") as f1:
                    request_token = f1.read().split("\n")

                a = flickr_api.auth.AuthHandler(
                    request_token_key=request_token[0],
                    request_token_secret=request_token[1]
                )

                # this will throw an exception if the verifier doesn't match the request_token
                a.set_verifier(args.user_auth_verifier)

                flickr_api.set_auth_handler(a)

                user = flickr_api.test.login()
                print("Authorized user:", user)

                if not os.path.exists('users'):
                    os.mkdir('users')
                a.save("users/" + user.username)

                os.remove(f)

                return
            except OSError:
                # continue trying
                pass

        exit("No matching pre-authorization found")

    if args.user_delete:
        try:
            os.remove('users/' + args.user_delete)
        except Exception:
            print("Could not remove the user")
            raise
        return

    if args.user_old_auth:
        # handle old-style auth directly, since flickr_api only handled OAuth
        m = hashlib.md5()
        m.update(state.get('main', 'api_secret'))
        m.update(b'api_key')
        m.update(state.get('main', 'api_key'))
        m.update(b'auth_token')
        m.update(args.user_old_auth)
        m.update(b'format')
        m.update(b'json')
        m.update(b'method')
        m.update(b'flickr.auth.oauth.getAccessToken')
        m.update(b'nojsoncallback')
        m.update(b'1')

        url = "https://api.flickr.com/services/rest/" \
              "?method=flickr.auth.oauth.getAccessToken" \
              "&api_key={0}" \
              "&auth_token={1}" \
              "&format=json" \
              "&nojsoncallback=1" \
              "&api_sig={2}".format(
                  state.get('main', 'api_key'),
                  args.user_old_auth,
                  m.hexdigest()
              )

        resp = urllib.request.urlopen(url)
        response = json.load(resp)

        if response['stat'] != 'ok':
            exit("Request failed, Flickr responded: " + response['message'])

        access_token = response['auth']['access_token']

        # exchange old-style auth token for OAuth credentials;
        # Flickr disables the old token immediately
        a = flickr_api.auth.AuthHandler(
            access_token_key=str(access_token['oauth_token']),
            access_token_secret=str(access_token['oauth_token_secret']))

        flickr_api.set_auth_handler(a)

        user = flickr_api.test.login()
        print("Authorized user:", user)

        if not os.path.exists('users'):
            os.mkdir('users')
        a.save("users/" + user.username)
        return

    # get photos and send email
    user_photos = {}
    user_photos_by_taken = {}
    users = {}
    num_photos = 0

    user_profiles = glob.glob("users/*")

    if not len(user_profiles):
        exit("Please authorize users (no registered users yet)")

    for f in user_profiles:
        flickr_api.set_auth_handler(flickr_api.auth.AuthHandler.load(f))

        username = os.path.basename(f)

        last_date = state.getint('main', 'last_date')
        photos = flickr_api.Photo.recentlyUpdated(min_date=last_date,
                                                  extras=['url_m', 'url_o', 'description',
                                                          'date_taken'])

        if photos.data:
            info = flickr_api.test.login().getInfo()

            info['buddyicon'] = "https://farm{iconfarm}.staticflickr.com/{iconserver}/" \
                                "buddyicons/{nsid}.jpg" \
                .format(**info)

            photos.data = list(
                filter(lambda x: x.ispublic or x.isfriend or x.isfamily, photos.data))

            for photo in photos.data:
                # noinspection PyProtectedMember
                photo._set_properties(
                    flickr_url="https://www.flickr.com/photos/{0}/{1}/".format(username, photo.id)
                )

            if args.verbose:
                pprint.pprint(photos)

            num_photos += len(photos.data)
            users[username] = info
            user_photos[username] = photos.data
            user_photos_by_taken[username] = sorted(photos.data, key=lambda x: x.datetaken)

    # noinspection PyTypeChecker
    state.set('main', 'last_date', int(time.time()))
    if not args.dry_run:
        write_state(state)

    if len(users) == 0 or num_photos == 0:
        if not args.quiet:
            print("No new content")
        return

    env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
    template = env.get_template('email.jinja2')
    text = template.render(user_photos=user_photos, users=users,
                           user_photos_by_taken=user_photos_by_taken)

    if args.verbose:
        print(text)

    if not args.dry_run:
        try:
            charset.add_charset('utf-8', charset.QP, charset.QP)
            msg = MIMEText(text, 'html', 'utf8')
            msg['From'] = state.get('main', 'smtp_from')
            to = get_state_array(state, 'main', 'smtp_to')
            cc = get_state_array(state, 'main', 'smtp_cc')
            bcc = get_state_array(state, 'main', 'smtp_bcc')
            msg['To'] = ",".join(to)
            msg['Cc'] = ",".join(cc)
            # msg['Bcc'] = ",".join(bcc) # Add BCC to sendmail, but not headers
            msg['Subject'] = state.get('main', 'smtp_subject')

            s = smtplib.SMTP()
            s.connect(state.get('main', 'smtp_server'), state.getint('main', 'smtp_port'))

            if args.smtp_debug:
                s.set_debuglevel(1)

            s.ehlo()

            if state.getboolean('main', 'smtp_tls'):
                s.starttls()

            if state.has_option('main', 'smtp_user') and state.has_option('main', 'smtp_password'):
                s.login(state.get('main', 'smtp_user'), state.get('main', 'smtp_password'))

            s.sendmail(state.get('main', 'smtp_from'), to + cc + bcc, msg.as_string())
            s.quit()
        except Exception:
            print("Can't send email, you can set SMTP options in state.ini: "
                  "set smtp_tls=true, smtp_user, smtp_pass for encrypted and authenticated SMTP")
            raise

    if not args.quiet:
        print("Sent email containing {0} photos from {1} users".format(
            len([item for sublist in user_photos.values() for item in sublist]),
            len(users)
        ))


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
