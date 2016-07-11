import json, requests, sys, urllib2, sqlite3, getopt, os, textwrap, datetime, urllib
from pprint import pprint
from collections import OrderedDict
from lxml import etree

class JSONConfig:
	def __init__(self):
		self.cookiePresent = False
		self.username = self.passkey = ''
		self.outputdir = 'watchdir/'
		self.cookie = OrderedDict([('uid',''),('pass',''),('hash','')])

	def read(self, filename):
		fileBasePath = os.path.dirname(os.path.realpath(__file__))
		try:
			with open(os.path.join(fileBasePath,filename),'r') as json_data:
				jsonConfig = json.load(json_data)
				json_data.close()
		except IOError:
			print "ERROR: config.json not found or not readable. Please run again with --makconf"
			exit(1)
		except:
			print "ERROR: config.json is invalid. Please recreate with --makeconf"
			exit(1)

		try:
			self.username = jsonConfig['username']
			self.passkey = jsonConfig['passkey']
			self.outputdir = jsonConfig['outputdir']
			if jsonConfig['cookie']['uid'] != "":
				self.cookiePresent = True
				self.c_uid = jsonConfig['cookie']['uid']
				self.c_pass = jsonConfig['cookie']['pass']
				self.c_hash = jsonConfig['cookie']['hash']
				self.cookie = {'uid':self.c_uid,'pass':self.c_pass,'hash':self.c_hash}
		except KeyError:
			pass

	def fileExists(self, filename):
		fileBasePath = os.path.dirname(os.path.realpath(__file__))
		try:
			with open(os.path.join(fileBasePath,filename),'r') as json_data:
				json_data.close()
				return True
		except IOError:
			return False

	def write(self, filename):
		#cookieJson = OrderedDict([('uid',self.c_uid),('pass',self.c_pass),('hash',self.c_hash)])
		fileBasePath = os.path.dirname(os.path.realpath(__file__))
		data = OrderedDict([('username',self.username),('passkey',self.passkey),('outputdir',os.path.abspath(self.outputdir)),('cookie',self.cookie)])
		try:
			with open(os.path.join(fileBasePath,filename), 'w') as outfile:
				json.dump(data, outfile, indent=4, separators=(',', ': '))
		except IOError:
			print "ERROR: Cannot write config.json"
			exit(1)

	def hasCookie(self):
		return self.cookiePresent

	#def validateUser(self):
	#	i=0

	def setCookie(self, cookie):
		self.cookie = cookie
		if cookie['uid'] != '' and cookie['pass'] != '' and cookie['hash'] != '':
			self.cookiePresent = True
		else:
			self.cookiePresent = False

	def getCookie(self):
		return self.cookie

	def setBaseConfig(self, config):
		self.username = config['username']
		self.passkey = config['passkey']
		self.outputdir = config['outputdir']

	def getBaseConfig(self):
		return {'username':self.username,'passkey':self.passkey,'outputdir':self.outputdir}

def isDownloaded(id):
	#checks if the id is in the downloaded list
	cur = conn.cursor()
	cur.execute('SELECT * FROM complete WHERE id=?', (id,))
	return False if len(cur.fetchall()) == 0 else True

def isWatched(id):
	#checks if the id is in the watchlist
	cur = conn.cursor()
	cur.execute('SELECT * FROM watched WHERE id=?', (id,))
	return False if len(cur.fetchall()) == 0 else True

def fetchTorrent(id, outputdir, sslVerify=True, allowDupes=False):
	#fetches torrent based on the given torrent id.  checks the database if it's already been downloaded.
	#if not, it downloads it.
	cfg = JSONConfig()
	cfg.read('config.json')

	username = cfg.getBaseConfig()['username']
	passkey = cfg.getBaseConfig()['passkey']
	outputdir = cfg.getBaseConfig()['outputdir']

	if isDownloaded(id) == False or allowDupes:
		apiUrl = 'https://hdbits.org/api/torrents'
		fetchPayload = {"username":username,"passkey":passkey,"limit":"1","id":id}
		try: 
			fetchResponse = requests.post(apiUrl, data=json.dumps(fetchPayload), headers=headers, verify=sslVerify, timeout=5)
		except requests.Timeout:
			print "Connection Error: API Timeout exceeded"
			exit(1)
		except:
			print "Connection Error: API down or unreachable"
			exit(1)	
		fetchData = json.loads(fetchResponse.text)
		torrentUrl = "https://hdbits.org/download.php?id=" + str(fetchData['data'][0]['id']) + "&passkey=" + passkey
		idStr = str(fetchData['data'][0]['id'])
		nameStr = fetchData['data'][0]['filename']
		fullPath = os.path.join(outputdir,nameStr)
		print "fetching: " + nameStr + " at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		#save .torrent file
		torrentFile = urllib2.urlopen(torrentUrl)
		try:
			with open(fullPath,'wb') as output:
				output.write(torrentFile.read())
			if verbose:
				print "writing .torrent file to " + fullPath
		except IOError:
			print "ERROR: could not write " + fullPath
			exit(1) 
		#log download to database
		conn.execute('''INSERT INTO complete(id, name) VALUES(?,?)''', (idStr, nameStr))
		conn.commit()
	elif debug:
		print "already fetched: " + str(id)

def loadQueueFile(queueFilename):
	parser = etree.HTMLParser()
	parsedPage = etree.parse(queueFilename, parser)

def populateWatchlist(parsedPage):
	#checks given filename, extracts all the ID #s from the links, and adds that list to the db
	hyperlinks = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/@href") 
	names = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/text()")
	conn.execute('''DROP TABLE watched''')
	conn.execute('''CREATE TABLE IF NOT EXISTS watched(idx INT, id INT, name TEXT)''')
	i=0
	for x in hyperlinks:
		if not isDownloaded(x[15:]):
			#encode/decode stuff required to avoid unicode errors in Windows and SQL
			if verbose:
				print names[i].encode('ascii', 'ignore').decode('ascii') + " added to watchlist"
			idStr = str(x[15:])
			indexStr = str(i)
			nameStr = names[i].encode('ascii', 'ignore').decode('ascii')
			conn.execute('''INSERT INTO watched(idx,id,name) VALUES(?,?,?)''', (indexStr, idStr, nameStr))
		i+=1
	if i == 0:
		print "Warning: no items found to add to watchlist"
	else:
		print i + "items added to watchlist"
	conn.commit()

def generateConfigFile(sslVerify=True):
	validResponse = cookieIsSet = False
	fileBasePath = os.path.dirname(os.path.realpath(__file__))

	cfg = JSONConfig()
	if cfg.fileExists('config.json'): 
		cfg.read('config.json')

	while True:
		usernameInput = raw_input("Please input your hdbits username: [" + cfg.getBaseConfig()['username'] + "] ")
		passkeyInput = raw_input("Please input your hdbits passkey: [" + cfg.getBaseConfig()['passkey'] + "] ")
		outputdirInput = raw_input(".torrent file output directory: [" + cfg.getBaseConfig()['outputdir'] + "] ")

		#if no input, go with default input
		if len(usernameInput) == 0: usernameInput = cfg.getBaseConfig()['username']
		if len(passkeyInput) == 0: passkeyInput = cfg.getBaseConfig()['passkey']
		if len(outputdirInput) == 0: outputdirInput = cfg.getBaseConfig()['outputdir']
		absOutputdir = os.path.abspath(outputdirInput)

		#Checking outputdir path
		if os.path.exists(absOutputdir) == False:
			while True:
				a = raw_input("Warning: path does not exist, create? (y/n) ")
				if a == 'y':
					try:
						os.makedirs(absOutputdir)
					except:
						print "ERROR: Could not create directory"
					break
				elif a == 'n':
					break
		
		#configure cookie
		while True:
			a = raw_input("Would you like to set a cookie? (y/[n]) ")
			if a == 'y':
				cookieIsSet = True
				c_uid = raw_input("Please input your cookie uid: [" + cfg.getCookie()['uid'] + "] ")
				c_pass = raw_input("Please input your cookie pass: [" + cfg.getCookie()['pass'] + "] ")
				c_hash = raw_input("Please input your cookie hash: [" + cfg.getCookie()['hash'] + "] ")
				#if no response leave it unchanged
				if len(c_uid) == 0: c_uid = cfg.getCookie()['uid']
				if len(c_pass) == 0: c_pass = cfg.getCookie()['pass']
				if len(c_hash) == 0: c_hash = cfg.getCookie()['hash']
				break
			else:
				c_uid = c_pass = c_hash = ''
				break

		print "\nUsername: " + usernameInput
		print "Passkey: " + passkeyInput
		print "Output Directory: " + os.path.abspath(outputdirInput)
		if cookieIsSet:
			print "cookie uid = " + c_uid
			print "cookie pass = " + c_pass
			print "cookie hash = " + c_hash

		#check if data input is correct
		while True:
			a = raw_input("\nIs this correct? (y/n) ")
			if a == 'y':
				#checks api if the user/passkey is valid
				apiUrl = "https://hdbits.org/api/test"
				payload = {"username":usernameInput,"passkey":passkeyInput}
				headers = {'content-type': 'application/json'}
				try:
					response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=sslVerify, timeout=5)
				except requests.Timeout:
					print "Connection Error: API Timeout exceeded"
					exit(1)
				except:
					print "Connection Error: API down or unreachable"
					exit(1)
				testData = json.loads(response.text)
				if testData['status'] == 0:
					validResponse = True
					break
				else:
					print "ERROR: API authentication failure. Check username and passkey and try again"
					break
			elif a == 'n':
				#save inputs as defaults for next try
				#cfg.setCookie({'uid':c_uid,'pass':c_pass,'hash':c_hash})
				#cfg.setBaseConfig({'username':usernameInput,'passkey':passkeyInput,'outputdir':outputdirInput})
				break
		if validResponse:
			break

	#write config file
	cfg.setCookie({'uid':c_uid,'pass':c_pass,'hash':c_hash})
	cfg.setBaseConfig({'username':usernameInput,'passkey':passkeyInput,'outputdir':outputdirInput})
	cfg.write('config.json')
	exit(0)

def displayHelp():
	print textwrap.dedent("""\
    pyhdbtools.py [OPTIONS] [FILE]

	RUN MODES

	-f, --fetch-free
		Checks the most recent 30 uploads and downloads any that are freeleech

	-F, --fetch-featured
		Checks the list of upcoming featured torrents and downloads any that are freeleech. High number 
		of API calls. Not recommended to be run more than once every 5 minutes.

	-h, --help
		display this help and exits

	--makeconf
		Generates json.config and exits

	-q, --scrape-queue
		fetches featuredqueue.html from hdbits.org and updates watchlist. Requires valid cookie set. Will
		likely get you banned. Use --update-featured instead.

	-t, -torrentid ######
		Download .torrent file of the matching id

	-u, --update-featured filename.html
		Processes the "Featured Torrents Queue"	page from hdbits and adds them to a watchlist. Local
		files only. Does not accept URLs avoid breaking rule prohibiting site scraping.

	--version
		Shows version number

	MODIFIERS

	--allowdupes
		Bypasses checks to not download dupes

	--noverify
		Skips SSL verification for API queries

	-v
		Verbose output
    """)
	exit(0)

def scrapeFeaturedQueue(sslVerify=True):
	cfg = JSONConfig()
	cfg.read('config.json')
	url = 'https://hdbits.org/featuredqueue.php'
	cookie = cfg.getCookie()
	r = requests.post(url, cookies=cookie, verify=sslVerify)

	parser = etree.HTMLParser()
	parsedPage = etree.XML(r.text.encode('utf8'), parser)

	populateWatchlist(parsedPage)

def main():
	global headers, verbose, conn, debug
	
	VERSION = 'build 071116 beta'

	#default options
	makeConf = updateFeatured = fetchFeatured = verbose = showVersion = dispHelp = allowDupes = singleTorrent = False
	fetchFree = debug = getQueue = False
	sslVerify = True

	#argument option handling
	options, remainder = getopt.getopt(sys.argv[1:], 'u:hs:VfFvq', ['update-featured=','fetch-featured','makeconf',
		'noverify','help','single-torrent','allowdupes','fetch-free','version','debug','scrape-queue'])
	for opt, arg in options:
		if opt in ('-v'):
			verbose = True
		elif opt in ('--noverify'):
			sslVerify = False
		elif opt in ('--makeconf'):
			makeConf = True
		elif opt in ('--allowdupes'):
			allowDupes = True
		elif opt in ('-u', '--update-featured'):
			updateFeatured = True
			queueFilename = arg
		elif opt in ('-F','--fetch-featured'):
			fetchFeatured = True
		elif opt in ('-h', '--help'):
			dispHelp = True
		elif opt in ('-s','--single-torrent'):
			singleTorrent = True
			torrentID = arg
		elif opt in ('-f','--fetch-free'):
			fetchFree = True
		elif opt in ('-V','--version'):
			showVersion = True
		elif opt in ('--debug'):
			debug = True
			verbose = True
		elif opt in ('-q','--scrape-queue'):
			getQueue = True

	if debug:
		print "starting run at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	if showVersion:
		print "pyhdbtools " + VERSION
		exit(0)

	if makeConf:
		generateConfigFile(sslVerify=sslVerify)

	if dispHelp:
		displayHelp()

	#importing config.json
	fileBasePath = os.path.dirname(os.path.realpath(__file__))
	cfg = JSONConfig()
	cfg.read('config.json')

	username = cfg.getBaseConfig()['username']
	passkey = cfg.getBaseConfig()['passkey']
	outputdir = cfg.getBaseConfig()['outputdir']

	headers = {'content-type': 'application/json'}

	#connect to database and create tables if they don't exist
	try:
		conn = sqlite3.connect(os.path.join(fileBasePath,'hdbits.db'))
	except IOError:
		print "ERROR: Permissions error at " + os.path.join(fileBasePath,'hdbits.db')
		exit(1) 

	conn.execute("CREATE TABLE IF NOT EXISTS complete(id INT, name TEXT)")
	conn.execute("CREATE TABLE IF NOT EXISTS watched(id INT, name TEXT)")

	if singleTorrent:
		fetchTorrent(torrentID, outputdir, sslVerify=sslVerify, allowDupes=allowDupes)
		exit(1)

	if updateFeatured:
		populateWatchlist(loadQueueFile(queueFilename))

	if getQueue:
		scrapeFeaturedQueue(sslVerify=sslVerify)
		exit(1)

	#fetch any freeleech in newest 30
	if fetchFree:
		apiUrl = 'https://hdbits.org/api/torrents'
		payload = {"username":username,"passkey":passkey,"limit":"30"}
		try:
			response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=sslVerify, timeout=5)
		except requests.Timeout:
			print "Connection Error: API Timeout exceeded"
			exit(1)
		except:
			print "Connection Error: API down or unreachable"
			exit(1)
		torrentData = json.loads(response.text)

		for x in torrentData['data']:
			if x['freeleech'] == 'yes':
				fetchTorrent(x['id'], outputdir, sslVerify=sslVerify, allowDupes=allowDupes)

	#Checks the first 7 entries in the watchlist and downloads them if freeleech
	if fetchFeatured:
		cur = conn.cursor()
		watchListTorrents = cur.execute('SELECT * FROM watched LIMIT 7')
		i = 0
		for row in watchListTorrents:
			apiUrl = 'https://hdbits.org/api/torrents'
			payload = {"username":username,"passkey":passkey,"limit":"1","id":row[1]}
			try:
				response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=sslVerify, timeout=5)
			except requests.Timeout:
				print "Connection Error: API Timeout exceeded"
				exit(1)
			except:
				print "Connection Error: API down or unreachable"
				exit(1)
			torrentData = json.loads(response.text)
			if isDownloaded(torrentData['data'][0]['id']):
				conn.execute('DELETE FROM watched WHERE id=?', (row[1],))
				conn.commit()
			elif torrentData['data'][0]['freeleech'] == "yes":
				fetchTorrent(torrentData['data'][0]['id'], outputdir, sslVerify=sslVerify, allowDupes=allowDupes)
				conn.execute('DELETE FROM watched WHERE id=?', (row[1],))
				conn.commit()
			i+=1
		if i == 0:
			print "Warning: watchlist is empty"
		cur.close()

	#terrible way of handling this.. fix someday
	if not (updateFeatured or fetchFeatured or fetchFree or singleTorrent or makeConf or showVersion or dispHelp or getQueue):
		print "ERROR: No runmode specified"
		displayHelp()

	conn.commit()
	conn.close()

if __name__ == "__main__":
    main()