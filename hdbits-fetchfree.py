import json, requests, sys, urllib2, pprint, sqlite3
from lxml import etree

def checkIfDownloaded(id):
	return True

def fetchTorrent(hash):
	#fetches torrent based on the given hash.  checks the database if it's already been downloaded.
	#if not, it downloads it.
	hash2 = (hash,)
	fetchPayload = {"username":username,"passkey":passkey,"limit":"1","hash":str(hash)}
	fetchResponse = requests.post(apiUrl, data=json.dumps(fetchPayload), headers=headers, verify=False)
	fetchData = json.loads(fetchResponse.text)
	hash2 = (fetchData['data'][0]['hash'],)
	cur.execute('SELECT * FROM complete WHERE hash=?', hash2)
	length = len(cur.fetchall())
	if length == 0:
		name2 = (fetchData['data'][0]['filename'],)
		torrentUrl = "https://hdbits.org/download.php?id=" + str(fetchData['data'][0]['id']) + "&passkey=" + passkey
		hashStr = str(fetchData['data'][0]['hash'])
		nameStr = str(fetchData['data'][0]['filename'])
		fullStr = watchdir + nameStr
		print "fetching: " + nameStr
		print torrentUrl
		torrentFile = urllib2.urlopen(torrentUrl)
		with open(fullStr,'wb') as output:
				output.write(torrentFile.read())
		cur.execute('''INSERT INTO complete(hash, name) VALUES(?,?)''', (hashStr, nameStr))
		return True;
	else:
		print "already fetched: " + str(fetchData['data'][0]['filename'])
		return False;

def populateWatchlist():
	#checks queue.html, extracts all the ID #s from the links, and adds that list to the db
	#sys.stdin.read(),sys.argv[1])
	parser = etree.HTMLParser()
	parsedPage = etree.parse("queue.html", parser)
	#result = etree.tostring(parsedPage.getroot(), pretty_print=True, method="html")
	hyperlinks = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/@href") 
	names = parsedPage.xpath("/html/body/table[3]/tr/td[2]/table/tr/td/table/tr/td/table/tr/td[1]/a/text()")
	i=0;
	for x in hyperlinks:
		#print x[15:]
		#print names[i]
		#print str(x[15:])
		cur.execute('SELECT * FROM watched WHERE id=?', (x[15:],))
		if len(cur.fetchall()) == 0:
			print x[15:] + "added to watchlist"
			idStr = str(x[15:])
			nameStr = names[i].encode('ascii', 'ignore').decode('ascii')
			cur.execute('''INSERT INTO watched(id,name) VALUES(?,?)''', (idStr, nameStr))
		#else:
		#	print x[15:] + "already added"
		i+=1
	#for x in names:
	#	print x

	#/html/body/table[3]/tbody/tr/td[2]/table/tbody/tr/td/table/tbody/tr/td/table/tbody/tr[2]/td[1]/a
	

def main():

	global conn, cur, username, passkey, watchdir, apiUrl, headers

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
	cur.execute("CREATE TABLE IF NOT EXISTS complete(hash TEXT, name TEXT)")
	cur.execute("CREATE TABLE IF NOT EXISTS watched(id INT, name TEXT)")

	#fetch any freeleech in newest 100
	payload = {"username":username,"passkey":passkey,"limit":"30"}
	response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
	torrentData = json.loads(response.text)

	for x in torrentData['data']:
		if x['freeleech'] == 'yes':
			fetchTorrent(str(x['hash']))

	#fetch any freeleech off the watchlist
	#currently checking first 5 to prevent hammering while testing
	j=0;
	for row in cur.execute('SELECT * FROM watched'):
	    if j>=5:
	    	break;
	    payload = {"username":username,"passkey":passkey,"limit":"1","id":row[0]}
	    response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
	    torrentData = json.loads(response.text)
	    
	    if torrentData['data'][0]['freeleech'] == "yes":
	    	fetchTorrent(str(torrentData['data'][0]['hash']))
	    	rowStr= str(row[0])
	    	print "row = " + rowStr
	    	cur.execute('DELETE FROM watched WHERE id=?', (row[0],))
	    else:
	    	print 'no match found'
	    j+=1

	populateWatchlist()

	conn.commit()
	conn.close()


if __name__ == "__main__":
    main()