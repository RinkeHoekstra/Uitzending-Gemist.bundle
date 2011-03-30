# -*- coding: utf-8 -*-
import re, time
from string import ascii_uppercase

###################################################################################################

PLUGIN_TITLE               = 'Uitzending Gemist (NPO)'
PLUGIN_PREFIX              = '/video/uzgv2'

UZG_BASE_URL               = 'http://www.uitzendinggemist.nl'
UZG_PLAYER_BASE_URL        = 'http://player.omroep.nl'
UZG_VIDEO_PAGE             = '%s/?aflID=%%s' % UZG_PLAYER_BASE_URL
UZG_PAGINATION_URLS        = 'pgNum='

UZG_DAY                    = '%s/index.php/selectie?searchitem=dag&dag=0&dagSelectie=%%d' % UZG_BASE_URL
UZG_BROADCASTER            = '%s/index.php/selectie?searchitem=omroep&omroep=%%d' % UZG_BASE_URL
UZG_AZ                     = '%s/index.php/selectie?searchitem=titel&titel=%%d' % UZG_BASE_URL
UZG_GENRE                  = '%s/index.php/selectie?searchitem=genre&genre=%%d' % UZG_BASE_URL

UZG_ARCHIVE                = '%s/index.php/serie?serID=%%d&md5=%%s' % UZG_BASE_URL
UZG_MORE_ARCHIVE           = '%s/index.php/serie2?serID=%%d&md5=%%s' % UZG_BASE_URL

UZG_TOP_50                 = '%s/index.php/top50' % UZG_BASE_URL
UZG_SEARCH_TITLE           = '%s/index.php/search?sq=%%s&search_filter=titel' % UZG_BASE_URL

METADATA_URL               = '%s/info/metadata/aflevering/%%s/%%s' % UZG_PLAYER_BASE_URL
STREAM_URL                 = '%s/sl/info/stream/aflevering/%%s/%%s' % UZG_PLAYER_BASE_URL

WEEKDAY                    = ['zondag','maandag','dinsdag','woensdag','donderdag','vrijdag','zaterdag']
MONTH                      = ['', 'januari','februari','maart','april','mei','juni','juli','augustus','september','oktober','november','december']

SILVERLIGHT_PLAYER         = 'http://www.plexapp.com/player/silverlight.php?stream=%s'

# Default artwork and icon(s)
PLUGIN_ARTWORK             = 'art-default.jpg'
PLUGIN_ICON_DEFAULT        = 'icon-default.png'
PLUGIN_ICON_SEARCH         = 'icon-search.png'
PLUGIN_ICON_PREFS          = 'icon-prefs.png'

###################################################################################################

def Start():
  Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, PLUGIN_TITLE, PLUGIN_ICON_DEFAULT, PLUGIN_ARTWORK)
  Plugin.AddViewGroup('_List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('_InfoList', viewMode='InfoList', mediaType='items')

  # Set the default MediaContainer attributes
  MediaContainer.title1    = PLUGIN_TITLE
  MediaContainer.viewGroup = '_InfoList'
  MediaContainer.art       = R(PLUGIN_ARTWORK)
  MediaContainer.userAgent = ''

  # Set HTTP headers
  HTTP.CacheTime = 1800
  HTTP.Headers['User-agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; en-US; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10'

###################################################################################################

def MainMenu():
  dir = MediaContainer(viewGroup='_List', noCache=True)
  EnsureSessionIsAlive()

  dir.Append(Function(DirectoryItem(Recent, title='Recente uitzendingen', thumb=R(PLUGIN_ICON_DEFAULT))))
  dir.Append(Function(DirectoryItem(AZ, title='Programma\'s A-Z', thumb=R(PLUGIN_ICON_DEFAULT))))
  dir.Append(Function(DirectoryItem(Channels, title='Zenders', thumb=R(PLUGIN_ICON_DEFAULT))))
  dir.Append(Function(DirectoryItem(Broadcasters, title='Omroepen', thumb=R(PLUGIN_ICON_DEFAULT))))
  dir.Append(Function(DirectoryItem(Genres, title='Genres', thumb=R(PLUGIN_ICON_DEFAULT))))
#  dir.Append(Function(InputDirectoryItem(Search, title='Zoeken...', prompt='Zoeken op programmatitel', thumb=R(PLUGIN_ICON_SEARCH))))
  return dir

###################################################################################################

def Recent(sender):
  dir = MediaContainer(viewGroup='_List', title2=sender.itemTitle)

  time_tuple = ( int(time.strftime('%Y')), int(time.strftime('%m')), int(time.strftime('%d')), 0, 0, 0, 0, 0, 0) # Forget DST...
  timestamp = int( time.mktime(time_tuple) ) + 3600 # ...just use +3600 for GMT+1 for NL

  # Calculate timestamps for the past 30 days
  for i in range(30):
    day_ts = timestamp - (i * 86400)

    t = time.gmtime(day_ts)
    w = int( time.strftime('%w', t) )
    d = str( time.strftime('%d', t) ).lstrip('0')
    m = int( time.strftime('%m', t) )
    title = ' '.join([WEEKDAY[w], d, MONTH[m]]).capitalize()

    today = False
    if i == 0:
      today = True

    dir.Append(Function(DirectoryItem(BrowseByDay, title=title, thumb=R(PLUGIN_ICON_DEFAULT)), day_ts=day_ts, today=today))

  return dir

###################################################################################################

def BrowseByDay(sender, day_ts, today):
  dir = MediaContainer(title2=sender.itemTitle)

  cacheTime = CACHE_1WEEK
  if today == True:
    cacheTime = 900

  dir = GetEpisodeList(sender=None, url=UZG_DAY % (day_ts), cacheTime=cacheTime)

  if len(dir) == 0:
    dir.header = 'Geen programma\'s'
    dir.message = 'Er staan voor deze dag nog geen programma\'s op Uitzending Gemist.'

  return dir

###################################################################################################

def GetEpisodeList(sender, url, cacheTime=CACHE_1WEEK):
  dir = MediaContainer()

  episodes = GetProgrammes(url, cacheTime=cacheTime, episodes=True)
  for e in episodes:
    summary = ''
    if e['date'] != None:
      date = e['date'].split('-')
      date = ' '.join([ date[2].lstrip('0'), MONTH[int(date[1])], date[0] ])
      summary += 'Datum: ' + date + '\n'
    if e['broadcaster'] != None:
      summary += 'Omroep: ' + ', '.join(e['broadcaster']) + '\n'
    if e['views'] != None:
      summary += 'Views: ' + e['views'] + '\n'

    dir.Append(Function(WebVideoItem(PlayVideo, title=e['series'], subtitle=e['title'], summary=summary + '\n' + e['summary'], rating=e['rating'], thumb=Function(GetThumb, thumb=e['thumb'], alt_thumb=e['alt_thumb'])), episode_id=e['episode_id'], h=e['h']))

  return dir

###################################################################################################

def GetProgrammes(url, page=1, cacheTime=CACHE_1WEEK, episodes=False):
  EnsureSessionIsAlive()
  prog = []

  programmes = HTML.ElementFromURL(''.join([url, '&', UZG_PAGINATION_URLS, str(page)]), encoding='iso-8859-1', errors='ignore', cacheTime=cacheTime).xpath('//thead[@id="tooltip_selectie"]/parent::table//tr[@class]')
  for p in programmes:
    if episodes == False:
      series_url = p.xpath('./td[2]//a')[0].get('href')
      series_id = re.search('serID=([0-9]+)', series_url).group(1)
      series = p.xpath('./td[2]//a')[0].text.encode('iso-8859-1').decode('utf-8').strip()
      prog.append( {'series_id': series_id, 'series': series} )
    else:
      episode_url = p.xpath('./td[last()]/a')[0].get('href')
      episode_id = re.search('aflID=([0-9]+)', episode_url).group(1)
      episode = GetEpisodeDetails(episode_id)

      views = p.xpath('./td[4]')[0].text
      if views == '0':
        episode['views'] = None
      else:
        episode['views'] = views

      rating = p.xpath('./td[5]/div[@class="waar"]')[0].text
      if rating == '0.0':
        episode['rating'] = None
      else:
        episode['rating'] = float(rating)*2 # NPO rating is 0-5, for Plex it's 0-10
      prog.append(episode)

  pagination = HTML.ElementFromURL(''.join([url, '&', UZG_PAGINATION_URLS, str(page)]), errors='ignore', cacheTime=cacheTime).xpath('//a[contains(text(),"volgende")]')
  if len(pagination) > 0:
    prog.extend( GetProgrammes(url, page=page+1, cacheTime=cacheTime, episodes=episodes) )

  return prog

###################################################################################################

def GetEpisodeDetails(episode_id):
  h = Helper.Run('wiet', episode_id).upper()
  info = XML.ElementFromURL(METADATA_URL % (episode_id, h), errors='ignore', cacheTime=CACHE_1MONTH)

  prog = {}
  prog['h'] = h
  prog['series_id'] = info.xpath('/aflevering/serie')[0].get('id')
  prog['episode_id'] = info.xpath('/aflevering')[0].get('id')
  prog['series'] = info.xpath('/aflevering/titel')[0].text.strip()
  try:
    prog['title'] = info.xpath('/aflevering/aflevering_titel')[0].text.strip()
  except:
    prog['title'] = None

  try:
    prog['summary'] = info.xpath('/aflevering/info')[0].text.strip()
  except:
    prog['summary'] = ''

  try:
    prog['date'] = info.xpath('/aflevering/gidsdatum')[0].text # YYYY-MM-DD
  except:
    prog['date'] = None

  try:
    broadcaster = []
    br = info.xpath('/aflevering/omroepen/omroep')
    for b in br:
      broadcaster.append( b.xpath('./name')[0].text )
  except:
    broadcaster = None
  prog['broadcaster'] = broadcaster

  try:
    prog['thumb'] = info.xpath('/aflevering/images/image[last()]')[0].text
  except:
    prog['thumb'] = None

  try:
    prog['alt_thumb'] = 'http://u.omroep.nl/n/a/' + info.xpath('/aflevering/images/original_image')[0].text
  except:
    prog['alt_thumb'] = None

  return prog

###################################################################################################

def GetProgrammeList(sender, url):
  dir = MediaContainer(viewGroup='_List', title2=sender.itemTitle)

  for programme in GetProgrammes(url, episodes=False):
    dir.Append(Function(DirectoryItem(GetArchivedEpisodes, title=programme['series'], thumb=R(PLUGIN_ICON_DEFAULT)), series_id=programme['series_id']))

  if len(dir) == 0:
    dir.header = 'Geen programma\'s'
    dir.message = 'Deze categorie bevat geen items.'

  return dir

###################################################################################################

def AZ(sender):
  dir = MediaContainer(viewGroup='_List', title2=sender.itemTitle)

  # 0-9
  dir.Append(Function(DirectoryItem(GetProgrammeList, title='0-9', thumb=R(PLUGIN_ICON_DEFAULT)), url=UZG_AZ % (0)))

  i = 1
  # A to Z
  for char in list(ascii_uppercase):
    dir.Append(Function(DirectoryItem(GetProgrammeList, title=char, thumb=R(PLUGIN_ICON_DEFAULT)), url=UZG_AZ % (i)))
    i = i+1

  return dir

###################################################################################################

def Channels(sender):
  dir = MediaContainer(viewGroup='_List', title2=sender.itemTitle)

  channel = HTML.ElementFromURL(UZG_BASE_URL, encoding='iso-8859-1', errors='ignore').xpath('//div[@id="nav_net"]//a')
  for c in channel:
    title = c.text.encode('iso-8859-1').decode('utf-8').strip()
    url = UZG_BASE_URL + c.get('href')

    dir.Append(Function(DirectoryItem(GetProgrammeList, title=title, thumb=Function(GetIcon, id=title)), url=url))

  return dir

###################################################################################################

def Broadcasters(sender):
  dir = MediaContainer(viewGroup='_List', title2=sender.itemTitle)

  broadcaster = HTML.ElementFromURL(UZG_BASE_URL, encoding='iso-8859-1', errors='ignore').xpath('//select[@id="omroep"]/option[@value!=""]')
  for b in broadcaster:
    title = b.text.encode('iso-8859-1').decode('utf-8').strip()
    id = int(b.get('value'))
    url = UZG_BROADCASTER % (id)

    dir.Append(Function(DirectoryItem(GetProgrammeList, title=title, thumb=Function(GetIcon, id=title)), url=url))

  return dir

###################################################################################################

def Genres(sender):
  dir = MediaContainer(viewGroup='_List', title2=sender.itemTitle)

  genre = HTML.ElementFromURL(UZG_BASE_URL, encoding='iso-8859-1', errors='ignore').xpath('//select[@id="genre"]/option[@value!=""]')
  for g in genre:
    title = g.text.encode('iso-8859-1').decode('utf-8').strip()
    id = int(g.get('value'))
    url = UZG_GENRE % (id)

    dir.Append(Function(DirectoryItem(GetProgrammeList, title=title, thumb=R(PLUGIN_ICON_DEFAULT)), url=url))

  return dir

###################################################################################################

def GetArchivedEpisodes(sender, series_id, more_archive=False, page=1):
  dir = MediaContainer(viewGroup='_InfoList', title2=sender.itemTitle, noCache=True)
  EnsureSessionIsAlive()

  if more_archive == False:
    get_and_forget = HTTP.Request(UZG_ARCHIVE % (int(series_id), GetMD5()), cacheTime=0).content # Let's grab this page twice so it works (yah, uhm... doesn't work otherwise, even after we did EnsureSessionIsAlive...)
    programmes = HTML.ElementFromURL(UZG_ARCHIVE % (int(series_id), GetMD5()), encoding='iso-8859-1', errors='ignore', cacheTime=0).xpath('//tbody[@id="afleveringen"]/parent::table//tr[@class]')
    for p in programmes:
      episode_url = p.xpath('./td[last()]/a')[0].get('href')
      episode_id = re.search('aflID=([0-9]+)', episode_url).group(1)
      episode = GetEpisodeDetails(episode_id)

      views = p.xpath('./td[4]')[0].text
      if views == '0':
        episode['views'] = None
      else:
        episode['views'] = views

      rating = p.xpath('./td[3]/span')[0].text
      if rating == '0.0':
        episode['rating'] = None
      else:
        episode['rating'] = float(rating)*2 # NPO rating is 0-5, for Plex it's 0-10

      summary = ''
      if episode['date'] != None:
        date = episode['date'].split('-')
        date = ' '.join([ date[2].lstrip('0'), MONTH[int(date[1])], date[0] ])
        summary += 'Datum: ' + date + '\n'
      if episode['broadcaster'] != None:
        summary += 'Omroep: ' + ', '.join(episode['broadcaster']) + '\n'
      if episode['views'] != None:
        summary += 'Views: ' + episode['views'] + '\n'

      dir.Append(Function(WebVideoItem(PlayVideo, title=episode['series'], subtitle=episode['title'], summary=summary + '\n' + episode['summary'], rating=episode['rating'], thumb=Function(GetThumb, thumb=episode['thumb'], alt_thumb=episode['alt_thumb'])), episode_id=episode['episode_id'], h=episode['h']))
  else:
    Log('komt nog!')

  if len(dir) == 0:
    dir.header = 'Geen programma\'s'
    dir.message = 'Er staan van dit programma geen afleveringen op Uitzending Gemist.'

  return dir

###################################################################################################

def PlayVideo(sender, episode_id, h):
  stream = XML.ElementFromURL(STREAM_URL % (episode_id, h), errors='ignore', cacheTime=CACHE_1MONTH).xpath('/streams/stream[@compressie_formaat="wmv" and @compressie_kwaliteit="bb"]/streamurl')[0].text.strip()
  return Redirect(WebVideoItem( SILVERLIGHT_PLAYER % (String.Quote(stream, usePlus=True)) ))

###################################################################################################

def GetThumb(thumb, alt_thumb, mimetype='image/jpeg'):
  if thumb != None or alt_thumb != None:
    try:
      image = HTTP.Request(thumb, cacheTime=CACHE_1MONTH).content
      if thumb[-4:4] == '.png':
        mimetype = 'image/png'
      return DataObject(image, mimetype)
    except:
      try:
        image = HTTP.Request(alt_thumb, cacheTime=CACHE_1MONTH).content
        if alt_thumb[-4:4] == '.png':
          mimetype = 'image/png'
        return DataObject(image, mimetype)
      except:
        pass

  return Redirect(R(PLUGIN_ICON_DEFAULT))

###################################################################################################

def GetIcon(id):
  # Channels
  if id == 'Nederland 1':
    return Redirect(R('icon-nederland1.png'))
  elif id == 'Nederland 2':
    return Redirect(R('icon-nederland2.png'))
  elif id == 'Nederland 3':
    return Redirect(R('icon-nederland3.png'))
  elif id == 'Z@PP' or id == 'Z@pp':
    return Redirect(R('icon-zapp.png'))

  # Broadcasters
  elif id == '3FM':
    return Redirect(R('icon-3fm.png'))
  elif id == 'AVRO':
    return Redirect(R('icon-avro.png'))
  elif id == 'BNN':
    return Redirect(R('icon-bnn.png'))
  elif id == 'EO':
    return Redirect(R('icon-eo.png'))
  elif id == 'IKON':
    return Redirect(R('icon-ikon.png'))
  elif id == 'KRO':
    return Redirect(R('icon-kro.png'))
  elif id == 'LLiNK':
    return Redirect(R('icon-llink.png'))
  elif id == 'MAX':
    return Redirect(R('icon-max.png'))
  elif id == 'NCRV':
    return Redirect(R('icon-ncrv.png'))
  elif id == 'NIO':
    return Redirect(R('icon-nio.png'))
  elif id == 'NOS':
    return Redirect(R('icon-nos.png'))
  elif id == 'NPS':
    return Redirect(R('icon-nps.png'))
  elif id == 'OHM':
    return Redirect(R('icon-ohm.png'))
  elif id == 'Omroep-nl':
    return Redirect(R('icon-omroep-nl.png'))
  elif id == 'OMROP FRYSLAN':
    return Redirect(R('icon-omrop-fryslan.png'))
  elif id == 'Radio 1':
    return Redirect(R('icon-radio1.png'))
  elif id == 'Radio 2':
    return Redirect(R('icon-radio2.png'))
  elif id == 'Radio 3':
    return Redirect(R('icon-radio3.png'))
  elif id == 'Radio 4':
    return Redirect(R('icon-radio4.png'))
  elif id == 'Radio 5':
    return Redirect(R('icon-radio5.png'))
  elif id == 'Radio 6':
    return Redirect(R('icon-radio6.png'))
  elif id == 'RVU':
    return Redirect(R('icon-rvu.png'))
  elif id == 'TELEAC':
    return Redirect(R('icon-teleac.png'))
  elif id == 'TROS':
    return Redirect(R('icon-tros.png'))
  elif id == 'VARA':
    return Redirect(R('icon-vara.png'))
  elif id == 'VPRO':
    return Redirect(R('icon-vpro.png'))
  elif id == 'Z@ppelin':
    return Redirect(R('icon-zappelin.png'))
  else:
    return Redirect(R(PLUGIN_ICON_DEFAULT))

###################################################################################################

def GetMD5():
  return Hash.MD5(str(time.time()))

###################################################################################################

def EnsureSessionIsAlive():
  # Visit the homepage and a random video page to have the necessary cookies/initiate a session/keep the current session alive.
  # If we don't do this, we cannot access any pages within the website and the XML files we need.
  video_url = HTML.ElementFromURL(UZG_BASE_URL, errors='ignore', cacheTime=0).xpath('//a[contains(@href,"' + (UZG_VIDEO_PAGE % '') + '")]')[0].get('href')
  video_page = HTTP.Request(video_url, cacheTime=0).content
