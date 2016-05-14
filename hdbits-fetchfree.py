import json, requests, sys, urllib2, pprint, sqlite3, getopt, os
from lxml import etree

def ifDownloaded(id):
	#checks if the id is in the downloaded list
	cur.execute('SELECT * FROM complete WHERE id=?', (id,))
	if len(cur.fetchall()) == 0:
		return False
	else:
		return True

def ifWatched(id):
	#checks if the id is in the watchlist
	cur.execute('SELECT * FROM watched WHERE id=?', (id,))
	if len(cur.fetchall()) == 0:
		return False
	else:
		return True

def fetchTorrent(id,watchdir):
	#fetches torrent based on the given torrent id.  checks the database if it's already been downloaded.
	#if not, it downloads it.
	fetchPayload = {"username":username,"passkey":passkey,"limit":"1","id":id}
	fetchResponse = requests.post(apiUrl, data=json.dumps(fetchPayload), headers=headers, verify=False)
	fetchData = json.loads(fetchResponse.text)
	filePath = os.path.dirname(os.path.realpath(__file__))

	if not ifDownloaded(id):
		torrentUrl = "https://hdbits.org/download.php?id=" + str(fetchData['data'][0]['id']) + "&passkey=" + passkey
		idStr = str(fetchData['data'][0]['id'])
		nameStr = str(fetchData['data'][0]['filename'])
		fullStr = watchdir + nameStr
		if fullStr[:1] != "/" or fullStr[:1] != "~":
			fullStr = filePath + "/" + fullStr
		print "fetching: " + nameStr
		torrentFile = urllib2.urlopen(torrentUrl)
		with open(fullStr,'wb') as output:
				output.write(torrentFile.read())
		cur.execute('''INSERT INTO complete(id, name) VALUES(?,?)''', (idStr, nameStr))

def populateWatchlist(queueFilename):
	#checks queue.html, extracts all the ID #s from the links, and adds that list to the db
	parser = etree.HTMLParser()
	parsedPage = etree.parse(queueFilename, parser)
	hyperlinks = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/@href") 
	names = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/text()")
	cur.execute('''DROP TABLE watched''')
	cur.execute('''CREATE TABLE IF NOT EXISTS watched(id INT, name TEXT)''')
	i=0;
	for x in hyperlinks:
		if not ifDownloaded(x[15:]) and not ifWatched(x[15:]):
			print names[i] + " added to watchlist"
			idStr = str(x[15:])
			nameStr = names[i].encode('ascii', 'ignore').decode('ascii')
			cur.execute('''INSERT INTO watched(id,name) VALUES(?,?)''', (idStr, nameStr))
		i+=1	

def generateConfigFile():
	isCorrect = False
	usernameDefaultInput = ""
	passkeyDefaultInput = "" 
	watchdirDefaultInput = "watchdir/"

	while True:
		usernameInput = raw_input("Please input your hdbits username: [" + usernameDefaultInput + "] ")
		passkeyInput = raw_input("Please input your hdbits passkey: [" + passkeyDefaultInput + "] ")
		watchdirInput = raw_input(".torrent file output directory (relative or absolute): [" + watchdirDefaultInput + "] ") 

		if len(usernameInput) == 0:
			usernameInput = usernameDefaultInput
		if len(passkeyInput) == 0:
			passkeyInput = passkeyDefaultInput
		if len(watchdirInput) == 0:
			watchdirInput = watchdirDefaultInput

		if watchdirInput[-1:] != "/":
			watchdirInput = watchdirInput + "/"

		print "\n\nUsername: " + usernameInput
		print "Passkey: " + passkeyInput
		print "Output Directory: " + watchdirInput 

		while True:
			a = raw_input("\nIs this correct? (y/n) ")
			if a == 'y':
				payload = {"username":usernameInput,"passkey":passkeyInput}
				headers = {'content-type': 'application/json'}
				response = requests.post("https://hdbits.org/api/test", data=json.dumps(payload), headers=headers, verify=False)
				testData = json.loads(response.text)
				if testData['status'] == 0:
					isCorrect = True
					break
				else:
					print "Authentication failure. Check username or passkey"
					break
			elif a == 'n':
				usernameDefaultInput = usernameInput
				passkeyDefaultInput = passkeyInput
				watchdirDefaultInput = watchdirInput
				break
		if isCorrect:
			break

	data = {'username':usernameInput,'passkey':passkeyInput,'output_dir':watchdirInput}
	
	with open('config.json', 'w') as outfile:
		json.dump(data, outfile)
	os.chmod('config.json', 0600)

	exit(0)

def main():
	global cur, username, passkey, apiUrl, headers, filePath
	
	VERSION = 'build 051416 alpha'

	makeConf = updateFeatured = fetchFeatured = verbose = showVersion = False

	options, remainder = getopt.getopt(sys.argv[1:], 'u:fv', ['update-featured=','fetch-featured','makeconf','version'])

	for opt, arg in options:
		if opt in ('-u', '--update-featured'):
			updateFeatured = True
			queueFilename = arg
		elif opt in ('-f', '--fetch-featured'):
			fetchFeatured = True
		elif opt in ('--makeconf'):
			makeConf = True
		elif opt in ('-v'):
			verbose = True
		elif opt in ('--version'):
			showVersion = True

	if showVersion:
		print "hdbits-fetchfree " + VERSION
		exit(0)

	if makeConf:
		generateConfigFile()

	filePath = os.path.dirname(os.path.realpath(__file__))
	try:
		with open(filePath + "/config.json",'r') as json_data:
			jsonConfig = json.load(json_data)
			json_data.close()
	except IOError:
		print "config.json not found. Please run again with --makconf"
		exit(1)

	username = jsonConfig['username']
	passkey = jsonConfig['passkey']
	watchdir = jsonConfig['output_dir']

	apiUrl = 'https://hdbits.org/api/torrents'
	headers = {'content-type': 'application/json'}

	conn = sqlite3.connect(filePath + "/hdbits.db")
	cur = conn.cursor()
	cur.execute("CREATE TABLE IF NOT EXISTS complete(id INT, name TEXT)")
	cur.execute("CREATE TABLE IF NOT EXISTS watched(id INT, name TEXT)")

	#fetch any freeleech in newest 30
	payload = {"username":username,"passkey":passkey,"limit":"30"}
	response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
	torrentData = json.loads(response.text)

	for x in torrentData['data']:
		if x['freeleech'] == 'yes':
			fetchTorrent(x['id'],watchdir)

	#fetch any freeleech off the watchlist
	if fetchFeatured:
		for row in cur.execute('SELECT * FROM watched LIMIT 7'):
		    payload = {"username":username,"passkey":passkey,"limit":"1","id":row[0]}
		    response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
		    torrentData = json.loads(response.text)
		    
		    if torrentData['data'][0]['freeleech'] == "yes":
		    	fetchTorrent(torrentData['data'][0]['id'],watchdir)
		    	cur.execute('DELETE FROM watched WHERE id=?', (row[0],))

	if updateFeatured:
		populateWatchlist(queueFilename)

	conn.commit()
	conn.close()

if __name__ == "__main__":
    main()