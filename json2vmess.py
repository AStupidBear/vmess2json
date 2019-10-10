#!/usr/bin/env python3
import sys
import json
import base64
import argparse
import urllib.request

class UnknowProtocolException(Exception):
    pass

def get_host_ip():
    print("trying to get host ip address ...")
    req = urllib.request.Request(url="https://www.cloudflare.com/cdn-cgi/trace")
    with urllib.request.urlopen(req, timeout=5) as response:
        body = response.read().decode()
        for line in body.split("\n"):
            if line.startswith("ip="):
                _, _ip = line.split("=", maxsplit=2)
                if _ip != "":
                    print("using host ipaddress: {}, if not intended, use --addr option to specify".format(_ip))
                    return _ip
    return ""

def parse_inbounds(jsonobj):
    vmesses = []
    if "inbounds" in jsonobj:
        for ib in jsonobj["inbounds"]:
            if ib["protocol"] == "vmess":
                try:
                    vmesses += inbound2vmess(ib)
                except UnknowProtocolException:
                    pass

    for v in vmesses:
        link = "vmess://" + base64.b64encode(json.dumps(v, sort_keys=True).encode('utf-8')).decode()
        if option.debug:
            print(v)
        print(link)
        print()

def inbound2vmess(inbound):
    vmessobjs = []
    _add = host_ip
    _type = "none"
    _host = ""
    _path = ""
    _tls = ""
    _port = str(inbound["port"])
    _net = ""
    sset = {}

    if "streamSettings" in inbound:
        sset = inbound["streamSettings"]
    
    if "network" in sset:
        _net = sset["network"]
    else:
        _net = "tcp"

    if option.filter is not None:
        for filt in option.filter:
            if filt.startswith("!"):
                if _net == filt[1:]:
                    raise UnknowProtocolException()
            else:
                if _net != filt:
                    raise UnknowProtocolException()
    
    if _net == "tcp":
        if "tcpSettings" in sset and \
            "header" in sset["tcpSettings"] and \
            "type" in sset["tcpSettings"]["header"]:
                _type = sset["tcpSettings"]["header"]["type"]

        if "security" in sset:
            _tls = sset["security"]

    elif _net == "kcp":
        if "kcpSettings" in sset and \
            "header" in sset["kcpSettings"] and \
            "type" in sset["kcpSettings"]["header"]:
                _type = sset["kcpSettings"]["header"]["type"]

    elif _net == "ws":
        if "wsSettings" in sset and \
            "headers" in sset["wsSettings"] and \
            "Host" in sset["wsSettings"]["headers"]:
                _host = sset["wsSettings"]["headers"]["Host"]

        if "wsSettings" in sset and "path" in sset["wsSettings"]:
                _path = sset["wsSettings"]["path"]

        if "security" in sset:
            _tls = sset["security"]

    elif _net == "h2" or _net == "http":
        if "httpSettings" in sset and \
            "host" in sset["httpSettings"]:
                _host = ",".join(sset["httpSettings"]["host"])
        if "httpSettings" in sset and \
            "path" in sset["httpSettings"]:
                _path = sset["httpSettings"]["path"]
        _tls = "tls"

    elif _net == "quic":
        if "quicSettings" in sset:
            _host = sset["quicSettings"]["security"]
            _path = sset["quicSettings"]["key"]
            _type = sset["quicSettings"]["header"]["type"]

    else:
        raise UnknowProtocolException()

    if "settings" in inbound and "clients" in inbound["settings"]:
        for c in inbound["settings"]["clients"]:
            vobj = dict(
                id=c["id"], aid=str(c["alterId"]),
                v="2", tls=_tls, add=_add, port=_port, type=_type, net=_net, path=_path, host=_host, ps="{}/{}".format(_add, _net))

            if option.amend is not None:
                for am in option.amend:
                    k, v = am.split(":", maxsplit=2)
                    vobj[k] = v
            
            vmessobjs.append(vobj)
            
    return vmessobjs


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="json2vmess convert server side json into vmess links")
    parser.add_argument('--addr',
                        action="store",
                        default="",
                        help="server address. If not specified, program will detect the current IP")
    parser.add_argument('-f', '--filter',
                        action="append",
                        help="Protocol Filter, useful for inbounds with different protocols. "
                        "FILTER starts with ! means negative selection. Multiple filter is accepted.")
    parser.add_argument('-a', '--amend',
                        action="append",
                        help="Amend to the output values, can be use multiple times. eg: -a port:80 -a ps:amended")
    parser.add_argument('--debug',
                        action="store_true",
                        default=False,
                        help="debug mode, show vmess obj")
    parser.add_argument('json',
                        type=argparse.FileType('r'),
                        default=sys.stdin,
                        help="parse the server side json")

    option = parser.parse_args()

    host_ip = option.addr
    if host_ip == "":
        host_ip = get_host_ip()

    jsonobj = json.load(option.json)
    parse_inbounds(jsonobj)
