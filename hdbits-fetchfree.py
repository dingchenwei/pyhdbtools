import json, requests, sys, urllib2, pprint, sqlite3
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

def fetchTorrent(id):
	#fetches torrent based on the given torrent id.  checks the database if it's already been downloaded.
	#if not, it downloads it.
	fetchPayload = {"username":username,"passkey":passkey,"limit":"1","id":id}
	fetchResponse = requests.post(apiUrl, data=json.dumps(fetchPayload), headers=headers, verify=False)
	fetchData = json.loads(fetchResponse.text)
	if not ifDownloaded(id):
		name2 = (fetchData['data'][0]['filename'],)
		torrentUrl = "https://hdbits.org/download.php?id=" + str(fetchData['data'][0]['id']) + "&passkey=" + passkey
		idStr = str(fetchData['data'][0]['id'])
		nameStr = str(fetchData['data'][0]['filename'])
		fullStr = watchdir + nameStr
		print "fetching: " + nameStr
		torrentFile = urllib2.urlopen(torrentUrl)
		with open(fullStr,'wb') as output:
				output.write(torrentFile.read())
		cur.execute('''INSERT INTO complete(id, name) VALUES(?,?)''', (idStr, nameStr))
		return True;
	else:
		print "already fetched: " + str(fetchData['data'][0]['filename'])
		return False;

def populateWatchlist():
	#checks queue.html, extracts all the ID #s from the links, and adds that list to the db
	#sys.stdin.read(),sys.argv[1])
	parser = etree.HTMLParser()
	parsedPage = etree.parse("queue.html", parser)
	hyperlinks = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/@href") 
	names = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/text()")
	i=0;
	for x in hyperlinks:
		if not ifDownloaded(x[15:]) and not ifWatched(x[15:]):
			print x[15:] + " added to watchlist"
			idStr = str(x[15:])
			nameStr = names[i].encode('ascii', 'ignore').decode('ascii')
			cur.execute('''INSERT INTO watched(id,name) VALUES(?,?)''', (idStr, nameStr))
		#else:
		#	print x[15:] + "already added"
		i+=1	

def main():

	global cur, username, passkey, watchdir, apiUrl, headers

	with open('config.json') as json_data:
	    jsonConfig = json.load(json_data)
	    json_data.close()

	username = jsonConfig['username']
	passkey = jsonConfig['passkey']
	watchdir = jsonConfig['output_dir']

	apiUrl = 'https://hdbits.org/api/torrents'
	headers = {'content-type': 'application/json'}

	conn = sqlite3.connect('hdbits.db')
	cur = conn.cursor()
	cur.execute("CREATE TABLE IF NOT EXISTS complete(id INT, name TEXT)")
	cur.execute("CREATE TABLE IF NOT EXISTS watched(id INT, name TEXT)")

	#fetch any freeleech in newest 30
	payload = {"username":username,"passkey":passkey,"limit":"30"}
	response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
	torrentData = json.loads(response.text)

	for x in torrentData['data']:
		if x['freeleech'] == 'yes':
			fetchTorrent(str(x['id']))

	#fetch any freeleech off the watchlist
	#currently checking first 5 to prevent hammering while testing
	for row in cur.execute('SELECT * FROM watched LIMIT 5'):
	    payload = {"username":username,"passkey":passkey,"limit":"1","id":row[0]}
	    response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
	    torrentData = json.loads(response.text)
	    
	    if torrentData['data'][0]['freeleech'] == "yes":
	    	fetchTorrent(str(torrentData['data'][0]['id']))
	    	cur.execute('DELETE FROM watched WHERE id=?', (row[0],))
	    else:
	    	print 'no match found'

	populateWatchlist()

	conn.commit()
	conn.close()


if __name__ == "__main__":
    main()