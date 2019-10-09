#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is part of StalkPhish - see https://github.com/t4d/StalkPhish

import requests
from bs4 import BeautifulSoup
import re
import os
import io
import zipfile
import sys
import hashlib
from urllib.parse import urlparse
from tools.utils import TimestampNow
from tools.utils import SHA256
from tools.utils import UAgent
from tools.utils import ZipSearch
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def PKDownloadOpenDir(siteURL, siteDomain, IPaddress, TABLEname, InvTABLEname, DLDir, SQL, PROXY, LOG, UAFILE, ASN):
    global Ziplst
    proxies = {'http': PROXY, 'https': PROXY}
    UAG = UAgent()
    UA = UAG.ChooseUA(UAFILE)
    user_agent = {'User-agent': UA}
    now = str(TimestampNow().Timestamp())
    SHA = SHA256()
    Ziplst = []

    rhtml = requests.get(siteURL, headers=user_agent, proxies=proxies, allow_redirects=True, timeout=(5, 12), verify=False)
    thtml = BeautifulSoup(rhtml.text, 'html.parser')
    try:
        PageTitle = thtml.title.text.strip()
    except:
        PageTitle = None
    if PageTitle is not None:
        PageTitle = re.sub('\s+', ' ', PageTitle)
        SQL.SQLiteInvestigUpdateTitle(InvTABLEname, siteURL, PageTitle)
    else:
        pass

    thtmlatag = thtml.select('a')
    Ziplst += [siteURL + "/" + tag['href'] for tag in thtmlatag if '.zip' in tag.text]
    for file in Ziplst:
        try:
            r = requests.get(file, headers=user_agent, proxies=proxies, allow_redirects=True, timeout=(5, 12), verify=False)
            lastHTTPcode = str(r.status_code)
            # Reduce filename lenght
            if len(file) > 250:
                zzip = file.replace('/', '_').replace(':', '')[:250]
            else:
                zzip = file.replace('/', '_').replace(':', '')
            try:
                if zipfile.is_zipfile(io.BytesIO(r.content)):
                    savefile = DLDir + zzip
                    # Still collected file
                    if os.path.exists(savefile):
                        LOG.info("[DL ] Found still collected archive: " + savefile)
                        return
                    # New file to download
                    else:
                        LOG.info("[DL ] Found archive in an open dir, downloaded it as: " + savefile)
                        with open(savefile, "wb") as code:
                            code.write(r.content)
                            pass
                        ZipFileName = str(zzip + '.zip')
                        ZipFileHash = SHA.hashFile(savefile)
                        # Extract e-mails from downloaded file
                        try:
                            ZS = ZipSearch()
                            extracted_emails = str(ZS.PKzipSearch(InvTABLEname, SQL, LOG, DLDir, savefile)).strip("[]").replace("'", "")
                            LOG.info("[Emails] found: {}".format(extracted_emails))
                            SQL.SQLiteInvestigInsertEmail(InvTABLEname, extracted_emails, ZipFileName)
                        except Exception as e:
                            LOG.info("Extracted emails exception: {}".format(e))
                        return
                        SQL.SQLiteInvestigUpdatePK(InvTABLEname, siteURL, ZipFileName, ZipFileHash, now, lastHTTPcode)
                        return
                else:
                    pass
            except Exception as e:
                LOG.error("Error downloading file: {}".format(e))
        except requests.exceptions.ContentDecodingError:
            LOG.error("[DL ] content-type error")


# Connexion tests, Phishing kits downloadingd
def TryPKDownload(siteURL, siteDomain, IPaddress, TABLEname, InvTABLEname, DLDir, SQL, PROXY, LOG, UAFILE, ASN):
    global ziplist
    global PageTitle
    proxies = {'http': PROXY, 'https': PROXY}
    UAG = UAgent()
    UA = UAG.ChooseUA(UAFILE)
    user_agent = {'User-agent': UA}
    now = str(TimestampNow().Timestamp())
    SHA = SHA256()

    # PsiteURL = None
    # ResiteURL = siteURL
    # PsiteURL = urlparse(ResiteURL)
    # if len(PsiteURL.path.split("/")[1:]) >= 2:
    #     siteURL = ResiteURL.rsplit('/', 1)[0]
    # else:
    #     siteURL = ResiteURL

    # Let's try to find a phishing kit source archive
    try:
        r = requests.get(siteURL, headers=user_agent, proxies=proxies, allow_redirects=True, timeout=(5, 12), verify=False)
        # Generate page hash
        try:
            soup = BeautifulSoup(r.content, 'lxml')
            # Body hash only
            # body = soup.find('body')
            try:
                #page_body = body.findChildren()
                page_body = soup
            except:
                # print(r.content) ## print, frequently, JS in <head>
                pass
            try:
                sha1 = hashlib.sha1()
                sha1.update(repr(page_body).encode("utf-8"))
                PageHash = sha1.hexdigest()
                SQL.SQLiteInsertPageHash(TABLEname, siteURL, PageHash)
            except:
                pass
        except Exception as e:
            print(e)

        # if (str(r.status_code) != "404"):
        LOG.info("[" + str(r.status_code) + "] " + r.url)
        SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)
        if SQL.SQLiteInvestigVerifyEntry(InvTABLEname, siteDomain, IPaddress) is 0:
            SQL.SQLiteInvestigInsert(InvTABLEname, siteURL, siteDomain, IPaddress, now, str(r.status_code))
        else:
            pass
        ziplist = []
        path = siteURL
        pathl = '/' .join(path.split("/")[:3])
        pathlist = path.split("/")[3:]

        # Make list
        current = 0
        newpath = ""
        while current < len(pathlist):
            if current == 0:
                newpath = pathlist[current]
            else:
                newpath = newpath + "/" + pathlist[current]
            current = current + 1
            pathD = pathl + "/" + newpath
            ziplist.append(pathD)

        # Get page title
        try:
            if len(ziplist) >= 1:
                rhtml = requests.get(siteURL, headers=user_agent, proxies=proxies, allow_redirects=True, timeout=(5, 12), verify=False)
                thtml = BeautifulSoup(rhtml.text, 'html.parser')
                try:
                    PageTitle = thtml.title.text.strip()
                except:
                    PageTitle = None
                if PageTitle is not None:
                    PageTitle = re.sub('\s+', ' ', PageTitle)
                    LOG.info(PageTitle)
                    SQL.SQLiteInvestigUpdateTitle(InvTABLEname, siteURL, PageTitle)
                else:
                    pass
        except AttributeError:
            pass
        except requests.exceptions.ReadTimeout:
            pass
        except requests.exceptions.ConnectTimeout:
            pass
        except:
            err = sys.exc_info()
            LOG.error("Get PageTitle Error: " + siteURL + str(err))

        try:
            # Try to find and download phishing kit archive (.zip)
            if len(ziplist) > 1:
                for zip in ziplist:
                    if (' = ' or '%' or '?' or '-' or '@') not in os.path.basename(os.path.normpath(zip)):
                        try:
                            LOG.info("trying " + zip + ".zip")
                            rz = requests.get(zip + ".zip", headers=user_agent, proxies=proxies, allow_redirects=True, timeout=(5, 12), verify=False)
                            # if str(rz.status_code) != "404":
                            lastHTTPcode = str(rz.status_code)
                            # Reduce filename lenght
                            if len(zip) > 250:
                                zzip = zip.replace('/', '_').replace(':', '')[:250]
                            else:
                                zzip = zip.replace('/', '_').replace(':', '')
                            try:
                                if zipfile.is_zipfile(io.BytesIO(rz.content)):
                                    savefile = DLDir + zzip + '.zip'
                                    # Still collected file
                                    if os.path.exists(savefile):
                                        LOG.info("[DL ] Found still collected archive: " + savefile)
                                        return
                                    # New file to download
                                    else:
                                        LOG.info("[DL ] Found archive, downloaded it as: " + savefile)
                                        with open(savefile, "wb") as code:
                                            code.write(rz.content)
                                            pass
                                        ZipFileName = str(zzip + '.zip')
                                        ZipFileHash = SHA.hashFile(savefile)
                                        SQL.SQLiteInvestigUpdatePK(InvTABLEname, siteURL, ZipFileName, ZipFileHash, now, lastHTTPcode)
                                        # Extract e-mails from downloaded file
                                        try:
                                            ZS = ZipSearch()
                                            extracted_emails = str(ZS.PKzipSearch(InvTABLEname, SQL, LOG, DLDir, savefile)).strip("[]").replace("'", "")
                                            LOG.info("[Email] Found: {}".format(extracted_emails))
                                            SQL.SQLiteInvestigInsertEmail(InvTABLEname, extracted_emails, ZipFileName)
                                        except Exception as e:
                                            LOG.info("Extracted emails exception: {}".format(e))
                                        return
                                else:
                                    pass
                            except requests.exceptions.ContentDecodingError:
                                LOG.error("[DL ] content-type error")
                            except:
                                pass
                            # # 404
                            # else:
                            #     pass
                        except requests.exceptions.ReadTimeout:
                            LOG.debug("Connection Timeout: " + siteURL)
                        except requests.exceptions.ConnectTimeout:
                            LOG.debug("Connection Timeout")
                        except Exception as e:
                            LOG.error("Error Downloading zip: {}".format(e))
                            pass

                        # Search for OpenDir
                        try:
                            if PageTitle is not None:
                                if 'Index of' in PageTitle:
                                    PKDownloadOpenDir(zip, siteDomain, IPaddress, TABLEname, InvTABLEname, DLDir, SQL, PROXY, LOG, UAFILE, ASN)
                                else:
                                    pass
                            else:
                                pass
                        except Exception as e:
                            LOG.error("Potential OpenDir connection error: " + str(e))
                            pass
                    else:
                        pass
                else:
                    pass
            # Ziplist empty
            else:
                pass
        except Exception as e:
            LOG.error("DL Error: " + str(e))

        # else:
        #     LOG.debug("[" + str(r.status_code) + "] " + r.url)
        #     lastHTTPcode = str(r.status_code)
        #     SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, lastHTTPcode)
        #     SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)

    except requests.exceptions.ConnectionError:
        err = sys.exc_info()
        if '0x05: Connection refused' in err:
            SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Conn. refused')
        if '0x04: Host unreachable' in err:
            SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Unreachable')
        else:
            SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Conn. error')
        SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)
        LOG.debug("Connection error: " + siteURL)

    except requests.exceptions.ConnectTimeout:
        SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Conn. timeout')
        SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)
        LOG.debug("Connection Timeout: " + siteURL)

    except requests.exceptions.ReadTimeout:
        SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Conn. readtimeout')
        SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)
        LOG.debug("Connection Read Timeout: " + siteURL)

    except requests.exceptions.MissingSchema:
        SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Malformed URL')
        SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)
        LOG.debug("Malformed URL, skipping: " + siteURL)

    except requests.exceptions.InvalidURL:
        SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Malformed URL')
        SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)
        LOG.debug("Malformed URL, skipping: " + siteURL)

    except requests.exceptions.ChunkedEncodingError:
        SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Can\'t read data')
        SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)
        LOG.debug("Can't read data, skipping: " + siteURL)

    except requests.exceptions.TooManyRedirects:
        SQL.SQLiteInvestigUpdateCode(InvTABLEname, siteURL, now, 'Too many redirects')
        SQL.SQLiteInsertStillTryDownload(TABLEname, siteURL)
        LOG.debug("Too many redirects, skipping: " + siteURL)

    except KeyboardInterrupt:
        LOG.info("Shutdown requested...exiting")
        os._exit(0)

    except Exception as e:
        LOG.error("Error trying to find kit: " + str(e))
