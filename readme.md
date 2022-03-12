This script uses `nyaa.si` RSS feeds to push torrents to a Transmission client.
## `shows.yml` example
```yml
root: "H:/Videos/" #
shows:
 - - "search string"
   - "Download Folder"
   - 6 # episode to start at; optional

 - - "another search string"
   - "another download folder"
```