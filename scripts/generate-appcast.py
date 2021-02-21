#!/usr/bin/env python3
import json
from xml.etree import ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import email.utils

root = ET.Element("rss", attrib={
    "xmlns:sparkle": "http://www.andymatuschak.org/xml-namespaces/sparkle",
    "version": "2.0",
})
channel = ET.SubElement(root, "channel")
ET.SubElement(channel, "title").text = "iMast (β)"

current_builds = json.load(open("./builds.json", "r"))

for build in current_builds:
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = "{}b{}".format(build["version"], build["build_number"])
    print(email.utils.format_datetime(datetime.fromisoformat(build["created_at"].replace("Z", "+00:00"))))
    ET.SubElement(item, "pubDate").text = email.utils.format_datetime(datetime.fromisoformat(build["created_at"].replace("Z", "+00:00")))
    ET.SubElement(item, "sparkle:minimumSystemVersion").text = build["os_required"]
    if "patchnote" in build:
        ET.SubElement(item, "sparkle:releaseNotesLink", attrib={"xml:lang": "ja"}).text = build["patchnote"]
    ET.SubElement(item, "enclosure", attrib={
        "url": build["binary"]["url"],
        "sparkle:version": str(build["build_number"]),
        "sparkle:shortVersionString": build["version"],
        "length": str(build["binary"]["length"]),
        "type": "application/octet-stream",
        "sparkle:edSignature": build["binary"]["ed_sig"],
    })

with open("./dist/appcast-beta.xml", "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    f.write(minidom.parseString(ET.tostring(root, encoding="UTF-8")).toprettyxml(indent="    "))