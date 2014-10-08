# About

I wrote flickr_email because I couldn't find a way to notify friends and family members that new (private) pictures had been posted to my Flickr.

# Install

Install the dependencies with pip or easy_install:

- [Jinja2](http://jinja.pocoo.org/docs/dev/)
- [flickr_api](https://github.com/alexis-mignon/python-flickr-api/)

Clone the project: `git clone http://www.github.com/paour/flickr_email`

# Run

## Authorize the app

- Create a [new app](https://www.flickr.com/services/apps/create/) on Flickr

- Run `python flickr_email.py` once without arguments, which will create a file called `state.ini`

- Edit `state.ini` to provide your API_KEY and API_SECRET

- To add a user
	- Run `python flickr_email.py --user_add`, which provides a URL
	- Open the URL (you can send it to another user), and authorize the app, this will provide a result containing an oauth_verifier
	- Run `python flickr_email.py --user_auth_verifier <oauth_verifier>` to finalize authorizing the user

- You can also use an interactive authorization system or use an existing old (pre-OAuth) token (but be warned Flickr will then disable that token for other apps), see the help for more info

## Configure email parameters

- Edit `state.ini` and set the `smtp_from` and `smtp_to` parameters (if you're not using the local sendmail, you can set the `smtp_server`, `smtp_port`, `smtp_tls`, `smtp_user` and `smtp_password`)

- You can customize the `email.jinja2` file, which is a Jinga2 template and receives the `user_photos` (a dict of username: [flickr.photos.recentlyUpdated](https://www.flickr.com/services/api/flickr.photos.recentlyUpdated.html) associations), `user_photos_by_taken` (sorted by capture date rather than latest update) and `users` (a dict of username: [flickr.people.getInfo](https://www.flickr.com/services/api/flickr.people.getInfo.html) associations)

## Run the script

- Just run `python flickr_email.py` to cause emails to be sent; on first run, it will select photos from the last day and on subsequent runs, new photos since the last run (delete `last_date` in `state.ini` to reset)