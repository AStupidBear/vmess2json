# Vmess2Json

Simple script parses `vmess://` links into client v2ray config json. (`ss://` links also supported)
Currently only V2rayN/NG format is supported.

## Usage
```
usage: vmess2json.py [-h] [--parse_all] [--subscribe SUBSCRIBE] [-o OUTPUT]
                     [-u UPDATE] [--outbound] [--inbounds INBOUNDS]
                     [--secret SECRET]
                     [vmess]

vmess2json convert vmess link to client json config.

positional arguments:
  vmess                 A vmess:// link. If absent, reads a line from stdin.

optional arguments:
  -h, --help            show this help message and exit
  --parse_all           parse all vmess:// lines (or base64 encoded) from
                        stdin and write each into .json files
  --subscribe SUBSCRIBE
                        read from a subscribe url, display a menu to choose
                        nodes
  -o OUTPUT, --output OUTPUT
                        write to file. default to stdout
  -u UPDATE, --update UPDATE
                        update a config.json, changes only the first outbound
                        object.
  --outbound            output the outbound object only.
  --inbounds INBOUNDS   include inbounds objects, default:
                        "socks:1080,http:8123". Available proto:
                        socks,http,dns,mt,tproxy . For mtproto with custom
                        password: mt:7788:xxxxxxxxxxxxxxx
  --localdns LOCALDNS   use domestic DNS server for geosite:cn list domains.
```

## Example

Most common usage is to choose node from a subscribe source.
```
$ wget https://vmess.subscribe.domain/sub.txt
$ cat sub.txt | sudo vmess2json.py --inbounds http:8123,socks:7070 --output /etc/v2ray/config.json
Found 5 items.
[1] - [hk1] hk1.domain.co:8388/shadowsocks
[2] - [ca/kcp4] ca.domain.ml:17738/kcp
[3] - [ca/kcp6] ca6.domain.ml:17738/kcp
[4] - [ca/cf] caf.domain.ml:443/ws
[5] - [lit/ws] lit6.domain.ml:443/ws

Choose >>> 5
$ sudo systemctl restart v2ray
```

Or just update the `outbound` object for a well written `config.json`.
```
$ cat sub.txt | sudo vmess2json.py --update /etc/v2ray/config.json
$ sudo systemctl restart v2ray
```

And many more other usages...
```
# manualy check on a link (checkout outbound info)
vmess2json.py --outbound vmess://ABCDEFGabcdefg1234567890...
echo "vmess://ABCDEFGabcdefg1234567890..." | vmess2json.py --outbound

# convert a vmess link into a config.json with some inbounds.
vmess2json.py --inbounds http:8123,socks:7070,mt:8888 -o /etc/v2ray/config.json vmess://ABCDEFGabcdefg123456...

# wirte multiple .json (per line)
cat vmess_list.txt | vmess2json.py --parse_all

# choose from an online subscribe source
vmess2json.py --subscribe https://vmess.subscribe.domain/sub.txt -o /etc/v2ray/config.json
```

# VmessEditor

`vmesseditor.py` parses subscribtion files and allow user to edit one of the configs.

Editor accepets both base64 encoded or plain text subscribtion, but outputs only plain texts.

## Usage

Edit a subscription file `subs.txt`
```text
./vmesseditor.py subs.txt
==============================================================
[ 0 ] - [node/cf] node.domain.ml:443/ws
[ 1 ] - [node/kcp4] node.domain.ml:12738/kcp
[ 2 ] - [node/kcp6] node6.domain.ml:12738/kcp
[ 3 ] - [node/kcp4] node.domain.ml:1933/kcp
==============================================================
Enter index digit XX to edit,
Other commands: Add(a), Delete XX(dXX), Sort by ps(s), Sort by ps desc(d),
Save Write(w), Quit without saving(q)

Choose >>>
```

Now you can enter the index digit to edit one of the config, the script calls `vim` to open a template file with config content.

```json
{
    "v": "2",
    "ps": "node/cf",
    "add": "node.domain.net",
    "port": "443",
    "id": "2aaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "aid": "8",
    "net": "ws",
    "type": "none",
    "host": "",
    "path": "/abc123",
    "tls": "tls"
}
```

On save and exit `:wq`, scripts parses the context and return to the main menu.

Use command `w` to save and exit, now you have an updated subscribtion file.

OR:

Edit a single `vmess://` link
```
./vmesseditor.py vmess://abcdEFGHIJK....
```


# json2vmess

`json2vmess.py` works oppositely, parses a server side json and prints `vmess://` links.

## Usage

```
./json2vmess.py --help
usage: json2vmess.py [-h] [-a ADDR] json

json2vmess convert server side json into vmess links

positional arguments:
  json                  parse the server side json

optional arguments:
  -h, --help            show this help message and exit
  --addr ADDR           server address. If not specified, program will detect
                        the current IP
  --filter FILTER       Protocol Filter, useful for inbounds with different
                        protocols. FILTER starts with ! means negative
                        selection. Multiple filter is accepted.
  -a AMEND, --amend AMEND
                        Amend to the output values, can be use multiple times.
                        eg: -a port:80 -a ps:amended
  --debug               debug mode, show vmess obj
```

## Example
```
#just list the links (on server)
./json2vmess.py /etc/v2ray/config.json 

# if using h2/ws protocols, auto detected IP is not working, manually specify it
./json2vmess.py --addr my.v2ray.domain.net /etc/v2ray/config.json 

# json file has multiple inbounds with different protocols
# output those ws and h2 and replace to port 443 for the caddy/nginx is proxying the websocket at 443
./json2vmess.py --addr my.v2ray.domain.net --filter ws --amend port:443 --debug  /etc/v2ray/config.json 

# use raw IP address for kcp and tcp connections 
./json2vmess.py --addr 2001:1234:5678::9999 --filter kcp -f tcp --debug  /etc/v2ray/config.json

# or just any protocols other than websocket
./json2vmess.py --addr 2001:1234:5678::9999 --filter \!ws --debug  /etc/v2ray/config.json
```