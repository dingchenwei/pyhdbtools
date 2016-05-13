import json, requests, sys, urllib2, pprint, sqlite3, getopt, os
from lxml import etree

def ifDownloaded(id):
	#checks if the id is in the downloaded list
	id = str(id)
	cur.execute('SELECT * FROM complete WHERE id=?', (id,))
	if len(cur.fetchall()) == 0:
		return False
	else:
		return True

def ifWatched(id):
	#checks if the id is in the watchlist
	id = str(id)
	cur.execute('SELECT * FROM watched WHERE id=?', (id,))
	if len(cur.fetchall()) == 0:
		return False
	else:
		return True

def fetchTorrent(id):
	#fetches torrent based on the given torrent id.  checks the database if it's already been downloaded.
	#if not, it downloads it.
	id = str(id)
	fetchPayload = {"username":username,"passkey":passkey,"limit":"1","id":id}
	fetchResponse = requests.post(apiUrl, data=json.dumps(fetchPayload), headers=headers, verify=False)
	fetchData = json.loads(fetchResponse.text)
	if not ifDownloaded(id):
		torrentUrl = "https://hdbits.org/download.php?id=" + str(fetchData['data'][0]['id']) + "&passkey=" + passkey
		idStr = str(fetchData['data'][0]['id'])
		nameStr = str(fetchData['data'][0]['filename'])
		fullStr = watchdir + nameStr
		print "fetching: " + nameStr
		torrentFile = urllib2.urlopen(torrentUrl)
		with open(fullStr,'wb') as output:
				output.write(torrentFile.read())
		cur.execute('''INSERT INTO complete(id, name) VALUES(?,?)''', (idStr, nameStr))
	else:
		print "already fetched: " + str(fetchData['data'][0]['filename'])

def populateWatchlist(queueFilename):
	#checks queue.html, extracts all the ID #s from the links, and adds that list to the db
	parser = etree.HTMLParser()
	parsedPage = etree.parse(queueFilename, parser)
	hyperlinks = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/@href") 
	names = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/text()")
	cur.execute('''DROP TABLE watched''')
	cur.execute("CREATE TABLE IF NOT EXISTS watched(id INT, name TEXT)")
	i=0;
	for x in hyperlinks:
		if not ifDownloaded(x[15:]) and not ifWatched(x[15:]):
			print names[i] + " added to watchlist"
			idStr = str(x[15:])
			nameStr = names[i].encode('ascii', 'ignore').decode('ascii')
			cur.execute('''INSERT INTO watched(id,name) VALUES(?,?)''', (idStr, nameStr))
		#else:
		#	print x[15:] + " SKIPPED"
		i+=1	

def main():
	global cur, username, passkey, watchdir, apiUrl, headers
	updateFeatured = fetchFeatured = False

	options, remainder = getopt.getopt(sys.argv[1:], 'u:f', ['update-featured=','fetch-featured',])

	for opt, arg in options:
		if opt in ('-u', '--update-featured'):
			updateFeatured = True
			queueFilename = arg
		elif opt in ('-f', '--fetch-featured'):
			fetchFeatured = True

	filePath = os.path.dirname(os.path.realpath(__file__))

	with open(filePath + "/config.json") as json_data:
	    jsonConfig = json.load(json_data)
	    json_data.close()

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
			fetchTorrent(x['id'])

	#fetch any freeleech off the watchlist
	if fetchFeatured:
		for row in cur.execute('SELECT * FROM watched LIMIT 7'):
		    payload = {"username":username,"passkey":passkey,"limit":"1","id":row[0]}
		    response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
		    torrentData = json.loads(response.text)
		    
		    if torrentData['data'][0]['freeleech'] == "yes":
		    	fetchTorrent(torrentData['data'][0]['id'])
		    	cur.execute('DELETE FROM watched WHERE id=?', (row[0],))
		    #else:
		    #	print 'no match found'

	if updateFeatured:
		populateWatchlist(queueFilename)

	conn.commit()
	conn.close()

if __name__ == "__main__":
    main()