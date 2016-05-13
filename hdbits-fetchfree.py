import json, requests, sys, urllib2, pprint, sqlite3

def fetchTorrent(hash):
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
	cur.execute("CREATE TABLE IF NOT EXISTS watched(id INT)")

	#fetch any freeleech in newest 100
	payload = {"username":username,"passkey":passkey,"limit":"30"}
	response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
	torrentData = json.loads(response.text)

	for x in torrentData['data']:
		if x['freeleech'] == 'yes':
			fetchTorrent(str(x['hash']))

	#fetch any freeleech off the watchlist
	for row in cur.execute('SELECT * FROM watched'):
	    payload = {"username":username,"passkey":passkey,"limit":"1","id":row[0]}
	    response = requests.post(apiUrl, data=json.dumps(payload), headers=headers, verify=False)
	    torrentData = json.loads(response.text)
	    if torrentData['data'][0]['freeleech'] == "yes":
	    	fetchTorrent(str(torrentData['data'][0]['hash']))
	    	cur.execute('DELETE FROM watched WHERE id=?', row[0])
	    else:
	    	print 'no match found'

	conn.commit()
	conn.close()


if __name__ == "__main__":
    main()