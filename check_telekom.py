#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cookielib
import urllib
import urllib2
from bs4 import BeautifulSoup
import pickle
import smtplib
import sys


# Login URL
login_url = "https://mojtelekom.telekom.rs/Users/login?checkuser=false"
# Korisnicko ime
username = "tvoje_korisnicko_ime"
# Lozinka
password = "tvoja_lozinka"
# User agent
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36"
# Redirect URL
redirect_url = "https://mojtelekom.telekom.rs/web/moj-racun-listing-i-placanja"
# URL za detalje o placanju racuna
details_url = "https://mojtelekom.telekom.rs/MojRacun/Racuni"
# Logout URL
logout_url = "https://mojtelekom.telekom.rs/Users/RemoveUser"

# Mail
mail_server = "localhost"
mail_sender = "Telekom Racuni <tvoja_mail_adresa_sa_koje_saljes>"
mail_recipients = ["mail_adresa_primaoca"]
mail_subject = "Nov(i) Telekom racun(i)"

# Fajl u kome se cuvaju podaci, kako bi sledeci put moglo da se proveri da li ima promena
store_file = "check_telekom.dat"

# Ignorisi ove sifre korisnika
# Npr. ignore_sifre = ["1234567/1"]
ignore_sifre = []

# Ignorisi ove racune
ignore_racune = []

def conv_lat2ascii(string, encoding='utf-8'):
	"""
	Konvertuj srpska slova u ascii.
	"""
	LAT_TO_ASC = {
		# Uppser case
		u'Č': u'C',
		u'Ć': u'C',
		u'Đ': u'Dj',
		u'Š': u'S',
		u'Ž': u'Z',

		# Lower case
		u'č': u'c',
		u'ć': u'c',
		u'đ': u'dj',
		u'š': u's',
		u'ž': u'z',
	}

	#asc = string.decode(encoding)
	asc = string

	for l,a in LAT_TO_ASC.items():
		asc = asc.replace(l,a)
	return asc



_dict = {}

class MojTelekom(object):

    def __init__(self, login, password):
    	""" Start """
        self.login = login
        self.password = password

        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cj)
        )
        self.opener.addheaders = [
            ('User-agent', (user_agent))
        ]


    def loginToWeb(self):
        """ Handle login. This should populate our cookie jar. """
        login_data = urllib.urlencode({
            'username': self.login,
            'password': self.password,
        })
        response = self.opener.open(login_url, login_data)
        return ''.join(response.readlines())


    def parsePage(self):
		response = self.opener.open(redirect_url)
		content = ''.join(response.readlines()).decode('utf-8')
		content_soup = BeautifulSoup(content)
		logon_data = content_soup.find('div', {'id': 'logon-data'})
		user_name = conv_lat2ascii(logon_data.strong.string)

		_table = content_soup.find('table', {'class': 'racun-listing'}).tbody
		_tr = _table.findAll('tr')

		print "\nKorisnik: " + user_name + "\n"

		_dict[user_name] = {}

		for item in _tr:
			sifra_korisnika1 = item['data-tisid']
			sifra_korisnika2 = item['data-zrrb']
			sifra_korisnika = sifra_korisnika1 + '/' + sifra_korisnika2

			if sifra_korisnika in ignore_sifre:
				continue

			_dict[user_name][sifra_korisnika] = {}
			print "  > Sifra korisnika: " + sifra_korisnika 

			_td = item.findAll('td')
			adresa = conv_lat2ascii(_td[1].text)
			_dict[user_name][sifra_korisnika]['adresa'] = adresa
			print "    Adresa: " + adresa

			servisi_block = _td[2].div
			servisi = servisi_block.findAll('div')

			servisi_arr = []
			print "    Servisi:"
			for servis in servisi:
				servisi_arr.append(servis.text)
				_dict[user_name][sifra_korisnika]['servisi'] = servisi_arr
				print "       - " + conv_lat2ascii(servis.text)

			print ""

			self.getDetails(sifra_korisnika1,sifra_korisnika2,user_name)

			#print content

    def getDetails(self,tis_id,rb,user_name):
		post_data = urllib.urlencode({
			'tis_id': tis_id,
			'rb': rb
		})
		sifra_korisnika = tis_id + "/" + rb
		response = self.opener.open(details_url, post_data)
		content = ''.join(response.readlines()).decode('utf-8')
		content_soup = BeautifulSoup(content)

		_dict[user_name][sifra_korisnika]['racuni'] = {}

		try:
			details_data = content_soup.find('table', {'class': 'racun-listing-2'}).tbody
			_tr = details_data.findAll('tr')

			racuni_dict = {}
			#print "    Racuni:"
			for item in _tr:
				_td = item.findAll('td')
				poziv_na_broj = _td[0].text.strip()
				datum_zaduzenja = _td[1].text.strip()
				iznos_zaduzenja = _td[2].text.strip()
				status = conv_lat2ascii(_td[3].text.strip())

				sufix = 0
				for racun in _dict[user_name][sifra_korisnika]['racuni']:
					poziv_na_broj_sa_sufiksom = poziv_na_broj + '-' + str(sufix)
					if racun == poziv_na_broj or racun == poziv_na_broj_sa_sufiksom:
						sufix = sufix + 1

				if sufix > 0:
					poziv_na_broj = poziv_na_broj + '-' + str(sufix)				

				racuni_dict[poziv_na_broj] = {
					'status': status,
					'iznos': iznos_zaduzenja,
					'datum': datum_zaduzenja
				}
			
				_dict[user_name][sifra_korisnika]['racuni'] = racuni_dict
				#print "       - " + poziv_na_broj + " | " + datum_zaduzenja + " | " + iznos_zaduzenja + " | " + status

		except:
				print "    Ne postoje racuni za odabrani servis."

		print ""
		#print content	


    def logOut(self):
    	response = self.opener.open(logout_url)
    	return ''.join(response.readlines()).decode('utf-8')


print ""

print "-> Ucitavanje podataka od proslog puta"
try:
	olddict = pickle.load(open(store_file, "rb"))
except:
	print "Ne postoje podaci od proslog puta. Verovatno prvi put pokrecete skriptu za ovog korisnika."
	olddict = {}

mt = MojTelekom(username,password)

print "-> Prvo prijavljivanje"
mt.loginToWeb()

print "-> Drugo prijavljivanje"
r = mt.loginToWeb()

print "-> Parsiranje strane"
r = mt.parsePage()
#print r

print "-> Odjavljivanje"
#r = mt.logOut()

print "-> Poredjenje podataka"

#pprint(_dict)
#sys.exit(0)

msg = ""
for n_user_name in sorted(_dict):
	if n_user_name not in olddict:
		msg += "\nNov korisnik: " + n_user_name + "\n"
		for n_sifra_korisnika in sorted(_dict[n_user_name]):
			msg += "\nSifra korisnika (" + n_user_name + "): " + n_sifra_korisnika + "\n"

	else:
		for n_sifra_korisnika in sorted(_dict[n_user_name]):
			if n_sifra_korisnika not in olddict[n_user_name]:
				msg += "\nNova sifra korisnika (" + n_user_name + "): " + n_sifra_korisnika + "\n"

			for n_poziv_na_broj in sorted(_dict[n_user_name][n_sifra_korisnika]['racuni']):
				n_status = _dict[n_user_name][n_sifra_korisnika]['racuni'][n_poziv_na_broj]['status']
				if n_poziv_na_broj not in olddict[n_user_name][n_sifra_korisnika]['racuni']:
					msg += "\nNov racun za korisnika " + n_user_name + " (" + n_sifra_korisnika + "):\n\n"
					msg += "    - Poziv na broj: " + n_poziv_na_broj + "\n"
					msg += "    - Datum zaduzenja: " + _dict[n_user_name][n_sifra_korisnika]['racuni'][n_poziv_na_broj]['datum'] + "\n"
					msg += "    - Iznos: " + _dict[n_user_name][n_sifra_korisnika]['racuni'][n_poziv_na_broj]['iznos'] + "\n"
					msg += "    - Status: " + n_status + "\n"

				if n_status == "Nije placeno":
					mail_subject = "PODSETNIK: Nije placen racun!"
					msg += "\nPODSETNIK: Nije placen racun za korisnika " + n_user_name + " (" + n_sifra_korisnika + "):\n\n"
					msg += "    - Poziv na broj: " + n_poziv_na_broj + "\n"
					msg += "    - Datum zaduzenja: " + _dict[n_user_name][n_sifra_korisnika]['racuni'][n_poziv_na_broj]['datum'] + "\n"
					msg += "    - Iznos: " + _dict[n_user_name][n_sifra_korisnika]['racuni'][n_poziv_na_broj]['iznos'] + "\n"
					msg += "    - Status: " + n_status + "\n"				

if msg != "":
	print msg
	msg = "From: " + mail_sender + "\nTo: " + ', '.join(mail_recipients) + "\nSubject: " + mail_subject + "\n\n" + msg + "\n"
	
	# Send email
	s = smtplib.SMTP(mail_server)
	smtpres = s.sendmail(mail_sender, mail_recipients, msg)
	s.quit()

	if smtpres:
		errstr = ""
		for recip in smtpres.keys():
			errstr = """Could not delivery mail to: %s

			Server said: %s
		  	%s

		  	%s""" % (recip, smtpres[recip][0], smtpres[recip][1], errstr)

		raise smtplib.SMTPException, errstr

else:
	print "    Nema promena"

print "-> Snimanje podataka"
pickle.dump(_dict, open(store_file, "wb"))

#pprint(_dict)
