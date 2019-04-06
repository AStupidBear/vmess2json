#!/usr/bin/env python3
import os
import sys
import json
import base64
import pprint
import argparse
import random

TPL = {}
TPL["CLIENT"] = """
{
	"log": {
		"access": "",
		"error": "",
		"loglevel": "error"
	},
	"inbounds": [
		{
			"port": 1080,
			"listen": "::",
			"protocol": "socks",
			"settings": {
				"auth": "noauth",
				"udp": true,
				"ip": "127.0.0.1"
			},
			"streamSettings": null
		},
		{
			"port": 3128,
			"listen": "::",
			"protocol": "http"
		}
	],
	"outbounds": [
		{
			"protocol": "vmess",
			"settings": {
				"vnext": [
					{
						"address": "host.host",
						"port": 1234,
						"users": [
							{
								"id": "<TOBEFILLED>",
								"alterId": 0,
								"security": "auto"
							}
						]
					}
				]
			},
			"streamSettings": {
				"network": "tcp"
			},
			"mux": {
				"enabled": true
			},
			"tag": "proxy"
		},
		{
			"protocol": "freedom",
			"settings": {
				"response": null
			},
			"tag": "direct"
		}
	],
	"dns": {
		"servers": [
			"8.8.8.8",
			"8.8.4.4",
			"1.1.1.1"
		]
	},
	"routing": {
		"domainStrategy": "AsIs",
		"rules": [
			{
				"type": "field",
				"ip": [
					"geoip:private"
				],
				"outboundTag": "direct"
			},
			{
				"type": "field",
				"domain": [
					"geosite:cn"
				],
				"outboundTag": "direct"
			},
			{
				"type": "field",
				"domain": [
					"geoip:cn"
				],
				"outboundTag": "direct"
			}
		]
	}
}
"""

# tcpSettings
TPL["http"] = """
{
    "header": {
        "type": "http",
        "request": {
            "version": "1.1",
            "method": "GET",
            "path": [
                "/"
            ],
            "headers": {
                "Host": [
                    "www.cloudflare.com",
                    "www.amazon.com"
                ],
                "User-Agent": [
                    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.75 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0"
                ],
                "Accept": [
                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
                ],
                "Accept-language": [
                    "zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4"
                ],
                "Accept-Encoding": [
                    "gzip, deflate, br"
                ],
                "Cache-Control": [
                    "no-cache"
                ],
                "Pragma": "no-cache"
            }
        }
    }
}
"""

# kcpSettings
TPL["kcp"] = """
{
    "mtu": 1350,
    "tti": 50,
    "uplinkCapacity": 12,
    "downlinkCapacity": 100,
    "congestion": false,
    "readBufferSize": 2,
    "writeBufferSize": 2,
    "header": {
        "type": "wechat-video"
    }
}
"""

# wsSettings
TPL["ws"] = """
{
    "connectionReuse": true,
    "path": "/path",
    "headers": {
        "Host": "host.host.host"
    }
}
"""


# httpSettings
TPL["h2"] = """
{
    "host": [
        "host.com"
    ],
    "path": "/host"
}
"""

TPL["quic"] = """
{
  "security": "none",
  "key": "",
  "header": {
    "type": "none"
  }
}
"""

def parseVmess(vmesslink):
    """
    return:
{
  "v": "2",
  "ps": "remark",
  "add": "4.3.2.1",
  "port": "1024",
  "id": "xxx",
  "aid": "64",
  "net": "tcp",
  "type": "none",
  "host": "",
  "path": "",
  "tls": ""
}
    """
    vmscheme = "vmess://"
    if vmesslink.startswith(vmscheme):
        bs = vmesslink[len(vmscheme):]
        #paddings
        blen = len(bs)
        if blen % 4 > 0:
            bs += "=" * (4 - blen % 4)

        vms = base64.b64decode(bs)
        return json.loads(vms)
    else:
        raise Exception("vmess link invalid")

def load_TPL(stype):
    s = TPL[stype]
    return json.loads(s)

def fill_basic(_c, _v):
    _outbound = _c["outbounds"][0]
    _vnext = _outbound["settings"]["vnext"][0]

    _vnext["address"]               = _v["add"]
    _vnext["port"]                  = _v["port"]
    _vnext["users"][0]["id"]        = _v["id"]
    _vnext["users"][0]["alterId"]   = int(_v["aid"])

    _outbound["streamSettings"]["network"]  = _v["net"]

    if _v["tls"] == "tls":
        _outbound["streamSettings"]["security"] = "tls"

    return _c

def fill_tcp_http(_c, _v):
    tcps = load_TPL("http")
    tcps["header"]["type"] = _v["type"]
    if _v["host"]  != "":
        # multiple host
        tcps["header"]["request"]["headers"]["Host"] = _v["host"].split(",")

    if _v["path"]  != "":
        tcps["header"]["request"]["path"] = [ _v["path"] ]

    _c["outbounds"][0]["streamSettings"]["tcpSettings"] = tcps
    return _c

def fill_kcp(_c, _v):
    kcps = load_TPL("kcp")
    kcps["header"]["type"] = _v["type"]
    _c["outbounds"][0]["streamSettings"]["kcpSettings"] = kcps
    return _c

def fill_ws(_c, _v):
    wss = load_TPL("ws")
    wss["path"] = _v["path"]
    wss["headers"]["Host"] = _v["host"]
    _c["outbounds"][0]["streamSettings"]["wsSettings"] = wss
    return _c

def fill_h2(_c, _v):
    h2s = load_TPL("h2")
    h2s["path"] = _v["path"]
    h2s["host"] = [ _v["host"] ]
    _c["outbounds"][0]["streamSettings"]["httpSettings"] = h2s
    return _c

def fill_quic(_c, _v):
    quics = load_TPL("quic")
    quics["header"]["type"] = _v["type"]
    quics["security"]       = _v["host"]
    quics["key"]            = _v["path"]
    _c["outbounds"][0]["streamSettings"]["quicSettings"] = quics
    return _c

def vmess2client(_t, _v):
    _c = fill_basic(_t, _v)

    _net = _v["net"]
    _type = _v["type"]

    if _net == "kcp":
        return fill_kcp(_c, _v)
    elif _net == "ws":
        return fill_ws(_c, _v)
    elif _net == "h2":
        return fill_h2(_c, _v)
    elif _net == "quic":
        return fill_quic(_c, _v)
    elif _net == "tcp":
        if _type == "http":
            return fill_tcp_http(_c, _v)
        return _c
    else:
        pprint.pprint(_v)
        raise Exception("this link seem invalid to the script, please report to dev.")


def parseMultiple(lines):
    def genPath(ps, rand=False):
        # add random in case list "ps" share common names
        curdir = os.environ.get("PWD", '/tmp/')
        rnd = "-{}".format(random.randrange(100)) if rand else ""
        name = "{}{}.json".format(vc["ps"], rnd)
        return os.path.join(curdir, name)

    for line in lines:
        vc = parseVmess(line.strip())
        if int(vc["v"]) != 2:
            print("Version mismatched, skiped. This script only supports version 2.")
            continue

        cc = vmess2client(load_TPL("CLIENT"), vc)

        jsonpath = genPath(vc["ps"])
        while os.path.exists(jsonpath):
            jsonpath = genPath(vc["ps"], True)

        print("Wrote: " + jsonpath)
        with open(jsonpath, 'w') as f:
            jsonDump(cc, f)

def jsonDump(obj, fobj):
    if option.outbound:
        json.dump(obj["outbounds"][0], fobj, indent=4)
    else:
        json.dump(obj, fobj, indent=4)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="vmess2json convert vmess link to client json config.")
    parser.add_argument('-m', '--multiple',
                        action="store_true",
                        default=False,
                        help="read multiple lines from stdin, "
                             "each write to a json file named by remark, saving in current dir (PWD).")
    parser.add_argument('-o', '--output',
                        type=argparse.FileType('w'),
                        default=sys.stdout,
                        help="write output to file. default to stdout")
    parser.add_argument('-ob', '--outbound',
                        action="store_true",
                        default=False,
                        help="only output as an outbound object.")
    parser.add_argument('vmess',
                        nargs='?',
                        help="A vmess:// link. If absent, reads a line from stdin.")

    option = parser.parse_args()

    if option.multiple:
        parseMultiple(sys.stdin.readlines())
    else:
        if option.vmess is None:
            vmess = sys.stdin.readline()
        else:
            vmess = option.vmess

        vc = parseVmess(vmess.strip())
        if int(vc["v"]) != 2:
            print("ERROR: Vmess link version mismatch. This script only supports version 2.")
            sys.exit(1)
        cc = vmess2client(load_TPL("CLIENT"), vc)
        jsonDump(cc, option.output)
