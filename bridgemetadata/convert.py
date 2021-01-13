import os
import sys
from enum import Enum, auto
import lxml.etree as ET
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom

class UnimplementedConversionException(Exception):
    pass

class UnknownFormatException(Exception):
    pass    

class Format(Enum):

    QGIS = auto()
    ISO19139 = auto()
    ISO19115 = auto()
    DCAT = auto()
    DATACITE = auto()
    SCHEMA = auto()
    WRAPPING_ISO19115 = auto()
    FGDC = range(5)
    DIF = auto()
    EML = auto()


def _resource(f):
    return os.path.join(os.path.dirname(__file__), "resources", f) 

TO, FROM = range(2)

QMD_TO_ISO19139_XSLT = _resource("qgis-to-iso19139.xsl")
ISO19139_TO_SCHEMA = _resource("ISO19139-SCHEMA.xsl")
ISO19139_TO_QMD_XSLT = _resource("iso19139-to-qgis.xsl")
ISO19139_TO_DCAT_XSLT = _resource("iso-19139-to-dcat-ap.xsl")
ISO_TO_DATACITE = _resource("ISO19139-DATASITE.xsl")
DIF_TO_ISO = _resource("DIF-ISO-2.1.xsl")
EML_TO_ISO = _resource("eml/eml2iso19139.xsl")
ISO_TO_EML = _resource("eml/iso2eml.xsl")
ISO19115_TO_ISO19139_XSLT = _resource("iso19115-to-iso19139.xsl")
WRAPPING_ISO19115_TO_ISO19139_XSLT = _resource("iso19115-wrapping-to-iso19139.xsl")
FGDC_TO_ISO19115 = _resource("fgdc-to-iso19115.xsl")

conversion = {Format.QGIS: {TO: [ISO19139_TO_QMD_XSLT], FROM: [QMD_TO_ISO19139_XSLT]},
              Format.ISO19139: {TO: [], FROM: []},
              Format.ISO19115: {TO: None, FROM: [ISO19115_TO_ISO19139_XSLT]},
              Format.DCAT: {TO: [ISO19139_TO_DCAT_XSLT], FROM: None},
              Format.DATACITE: {TO: [ISO_TO_DATACITE], FROM: None},
              Format.SCHEMA: {TO: [ISO19139_TO_SCHEMA], FROM: None},
              Format.WRAPPING_ISO19115: {TO: None, FROM: [WRAPPING_ISO19115_TO_ISO19139_XSLT]},
              Format.FGDC: {TO: None, FROM: [FGDC_TO_ISO19115, ISO19115_TO_ISO19139_XSLT]},
              Format.DIF: {TO: None, FROM: [DIF_TO_ISO]},
              Format.EML: {TO: [ISO_TO_EML], FROM: [EML_TO_ISO]},
             }

def convert(src, dstformat, srcformat=None, dstfile=None):

    if os.path.exists(src):
        dom = ET.parse(src)
    else:
        dom = ET.fromstring(src)

    if srcformat is None:
        srcformat = _detect_format(dom)

    if srcformat is None:
        raise UnknownFormatException()

    to_conversion = conversion.get(dstformat)[TO]
    from_conversion = conversion.get(srcformat)[FROM]

    if None in [to_conversion, from_conversion]:
        raise UnimplementedConversionException()

    transforms = to_conversion + from_conversion

    for t in transforms:
        xslt = ET.parse(t)        
        transform = ET.XSLT(xslt)
        dom = transform(dom)

    s = ET.tostring(dom, pretty_print=True).decode()
    if dstfile is not None:        
        with open(dstfile, "w") as f:
            #only if this is a xml file
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + s)

    return s
    

def _detect_format(dom):
    root = dom.getroot()

    def _hasTag(tag,ns=None):
        return bool(len(list(root.xpath(f"//{tag}", namespaces=ns))))

    if _hasTag("qgis"):
        return Format.QGIS
    elif _hasTag("esri"):
        if _hasTag("gmd:MD_Metadata",{'gmd': 'http://www.isotc211.org/2005/gmd'}):
            return Format.WRAPPING_ISO19115
        else:
            return Format.ISO19115
    elif _hasTag("gmd:MD_Metadata",{'gmd': 'http://www.isotc211.org/2005/gmd'}) or _hasTag("MD_Metadata"):
        return Format.ISO19139
    elif _hasTag("metadata/mdStanName"):
        schemaName = list(root.iterfind("..//metadata/mdStanName"))[0].text
        if "FGDC-STD" in schemaName:
            return Format.FGDC
        elif "19115" in schemaName:
            return Format.ISO19139
    else:
        print ("Unknown source format")
        return None

def main():
    if len(sys.argv) != 4:
        print(
            "Wrong number of parameters\nUsage: convert src dst dest-format"
        )
    else:
        dst = None
        for f in Format:
            if str(f) == "Format."+sys.argv[3].upper():
                dst = f
        if (dst is None):
            raise UnknownFormatException(str(dst))
        convert(sys.argv[1], dst, None, sys.argv[2])
        print("Done")