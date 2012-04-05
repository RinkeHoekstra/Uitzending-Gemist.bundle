# -*- coding: utf-8 -*-
import re
from string import ascii_uppercase

###################################################################################################
PLUGIN_TITLE   = 'Uitzending Gemist'
UZG_BASE_URL   = 'http://www.uitzendinggemist.nl'
EPISODE_URL    = '%s/afleveringen/%%s' % UZG_BASE_URL
DATA_BASE_URL  = 'http://pi.omroep.nl'
UZG_PAGINATION = 'page=%d'
METADATA_URL   = '%s/info/metadata/aflevering/%%s/%%s' % DATA_BASE_URL
STREAM_URL     = '%s/info/stream/aflevering/%%s/%%s' % DATA_BASE_URL
MONTH          = ('', 'januari','februari','maart','april','mei','juni','juli','augustus','september','oktober','november','december')

ART            = 'art-default.jpg'
ICON           = 'icon-default.png'
ICON_SEARCH    = 'icon-search.png'
ICON_PREFS     = 'icon-prefs.png'

###################################################################################################
def Start():
  Plugin.AddPrefixHandler('/video/uzgv2', MainMenu, PLUGIN_TITLE, ICON, ART)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')
  
  MediaContainer.title1 = PLUGIN_TITLE
  MediaContainer.viewGroup = 'InfoList'
  MediaContainer.art = R(ART)
  
  DirectoryItem.thumb = R(ICON)
  WebVideoItem.thumb = R(ICON)
  
  HTTP.CacheTime = 300
  HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:5.0) Gecko/20100101 Firefox/5.0'

###################################################################################################
def MainMenu():
  dir = MediaContainer(viewGroup='List')
  
  dir.Append(Function(DirectoryItem(Recent, title='Afgelopen 7 dagen')))
  dir.Append(Function(DirectoryItem(Broadcaster, title='Programma\'s per Omroep')))
  dir.Append(Function(DirectoryItem(Genre, title='Programma\'s per Genre')))
  dir.Append(Function(DirectoryItem(AtoZ, title='Programma\'s A-Z')))
  
  return dir

###################################################################################################
def Recent(sender):
  dir = MediaContainer(viewGroup='List', title2=sender.itemTitle)
  
  for day in HTML.ElementFromURL(UZG_BASE_URL).xpath('//ol[@id="daystoggle"]/li/a'):
    title = re.sub('\s+', ' ', day.text)
    url = UZG_BASE_URL + day.get('href')
    dir.Append(Function(DirectoryItem(BrowseByDay, title=title), url=url))
  
  return dir

def Broadcaster(sender):
  dir = MediaContainer(title2=sender.itemTitle)
  
  bcListURL = UZG_BASE_URL + '/omroepen'
  
  for bc in HTML.ElementFromURL(bcListURL).xpath('//a[@class="broadcaster"]') :
    title = bc.get('title')
    bcurl = UZG_BASE_URL + bc.get('href')
    Log.Debug(bcurl)
    dir.Append(Function(DirectoryItem(BrowseByCategory, title=title, thumb=R('icon-'+title.lower()+'.png')), url=bcurl, heading='h3'))
  
  return dir

def Genre(sender):
  dir = MediaContainer(title2=sender.itemTitle)
  
  gListURL = UZG_BASE_URL + '/genres'
  
  for genre in HTML.ElementFromURL(gListURL).xpath('//a[@class="genre"]') :
    title = genre.get('title')
    genreurl = UZG_BASE_URL + genre.get('href')
    Log.Debug(genreurl)
    dir.Append(Function(DirectoryItem(BrowseByCategory, title=title), url=genreurl, heading='h3'))
  
  return dir

def AtoZ(sender):
  dir = MediaContainer(title2=sender.itemTitle)
  
  alphabet = 'abcdefghijklmnopqrstuvwxyz'
  numbers = '0-9'
  
  # First the letters
  for letter in list(alphabet) :
    title = letter.upper()
    atozurl = UZG_BASE_URL + '/programmas/' + letter
    Log.Debug(atozurl)
    dir.Append(Function(DirectoryItem(BrowseByCategory, title=title), url=atozurl, heading='h2'))
  
  # Then the numbers
  title = numbers
  atozurl = UZG_BASE_URL + '/programmas/' + numbers
  dir.Append(Function(DirectoryItem(BrowseByCategory, title=title), url=atozurl, heading='h2'))
  
  return dir


def BrowseByCategory(sender, url, heading='h3'):
  dir = MediaContainer(title2=sender.itemTitle)
  
  
  for page in range (1, NumberOfPages(url) + 1):
    for prog in HTML.ElementFromURL(url + '?' + (UZG_PAGINATION % page)).xpath('//'+heading+'/a[contains(@href, "/programmas/")]'):
      title = prog.get('title')
      progurl = UZG_BASE_URL + prog.get('href')
      Log.Debug(progurl)
      dir.Append(Function(DirectoryItem(BrowseByProg, title=title), url=progurl))
  
  return dir

def BrowseByProg(sender, url):  
  dir = MediaContainer(title2=sender.itemTitle)
  ids = []
  
  for page in range (1, NumberOfPages(url) + 1):
    for ep in HTML.ElementFromURL(url + '/afleveringen?' + (UZG_PAGINATION % page)).xpath('//h3/a[contains(@href, "/afleveringen/")]'):
      episode_id = re.search('/afleveringen/([0-9]+)', ep.get('href')).group(1)
      ids.append(episode_id)
  
  dir.Extend(Episodes(ids, is_recent_listing=False, is_single_program=True))
  
  if len(dir) == 0:
    dir.header = 'Geen programma\'s'
    dir.message = 'Er staan voor deze dag nog geen programma\'s op Uitzending Gemist.'
  
  return dir




###################################################################################################
def BrowseByDay(sender, url):
  dir = MediaContainer(title2=sender.itemTitle)
  ids = []
  
  for page in range (1, NumberOfPages(url) + 1):
    for ep in HTML.ElementFromURL(url + '?' + (UZG_PAGINATION % page)).xpath('//h3/a[contains(@href, "/afleveringen/")]'):
      episode_id = re.search('/afleveringen/([0-9]+)', ep.get('href')).group(1)
      ids.append(episode_id)
  
  dir.Extend(Episodes(ids, is_recent_listing=True))
  
  if len(dir) == 0:
    dir.header = 'Geen programma\'s'
    dir.message = 'Er staan voor deze dag nog geen programma\'s op Uitzending Gemist.'
  
  return dir

###################################################################################################
def NumberOfPages(url):
  try:
    num = HTML.ElementFromURL(url).xpath('//div[@class="pagination"]/a[not(@class)][last()]')[0].text
  except:
    num = 1
  
  return int(num)

###################################################################################################
def Episodes(ids, is_recent_listing=False, is_single_program=False):
  dir = MediaContainer()
  result_dict = {}
  
  
  @parallelize
  def GetEpisodes():
    for num in range(len(ids)):
      episode_id = ids[num]
      
      @task
      def GetEpisode(num=num, result_dict=result_dict, episode_id=episode_id):
        episode_link = HTML.ElementFromURL(EPISODE_URL % episode_id, cacheTime=CACHE_1MONTH).xpath('//meta[@property="og:video"]')[0].get('content')
        real_episode_id = re.search('episodeID=([0-9]+)', episode_link).group(1)
        metadataurl = METADATA_URL % (real_episode_id, GetHash(real_episode_id))
        metadata = XML.ElementFromURL(metadataurl, cacheTime=CACHE_1MONTH)
        Log.Debug(metadataurl)
        
        if metadata.xpath('/aflevering'):
          title = metadata.xpath('/aflevering/titel')[0].text.strip()
          
          try:
            subtitle = metadata.xpath('/aflevering/aflevering_titel')[0].text.strip()
            if is_single_program :
              title = subtitle
          except:
            subtitle = None
          
          summary = ''
          
          try:
            thumb = metadata.xpath('/aflevering/images/image[last()]')[0].text
          except:
            thumb = None
          
          try:
            alt_thumb = metadata.xpath('/aflevering/images/original_image')[0].text
            alt_thumb = 'http://u.omroep.nl/n/a/%s' % alt_thumb
          except:
            alt_thumb = None
          
          try:
            date = metadata.xpath('/aflevering/gidsdatum')[0].text # YYYY-MM-DD
          except:
            date = None
          
          try:
            time = metadata.xpath('/aflevering/streamSense/sko_t')[0].text # HHMM
            if time == '240':
              time = '00:00'
            elif len(time) < 4:
              time = None
            else:
              time = re.sub('(.{2})(.{2})', '\\1:\\2', time)
          except:
            time = None
          
          try:
            broadcaster = []
            br = metadata.xpath('/aflevering/omroepen/omroep')
            for b in br:
              broadcaster.append( b.xpath('./name')[0].text )
          except:
            broadcaster = None
          
          if date is not None:
            date = date.split('-')
            date = ' '.join([ date[2].lstrip('0'), MONTH[int(date[1])], date[0] ])
            summary += 'Datum: ' + date + '\n'
          
          if broadcaster is not None:
            summary += 'Omroep: ' + ', '.join(broadcaster) + '\n'
          
          try:
            summary += '\n' + metadata.xpath('/aflevering/info')[0].text.strip()
          except:
            summary += ''
          
          summary = summary.strip()
          
          if is_recent_listing and time is not None:
            title = time + ' ' + title
          
          result_dict[num] = VideoItem(Function(PlayVideo, real_episode_id=real_episode_id), title=title, subtitle=subtitle, summary=summary, thumb=Function(Thumb, url=thumb, alt_url=alt_thumb))
  
  keys = result_dict.keys()
  keys.sort()
  #keys.reverse()
  
  for key in keys:
    dir.Append(result_dict[key])
  
  return dir

###################################################################################################
def GetHash(episode_id):
  return Hash.MD5(''.join([episode_id, '|', '0.1 LSGUOPN'[::-1]])).upper()

###################################################################################################
def PlayVideo(sender, real_episode_id):
  try:
    stream = XML.ElementFromURL(STREAM_URL % (real_episode_id, GetHash(real_episode_id)), cacheTime=1).xpath('/streams/stream[@compressie_formaat="wvc1" and @compressie_kwaliteit="std"]/streamurl')[0].text.strip()
  except:
    try:
      stream = XML.ElementFromURL(STREAM_URL % (real_episode_id, GetHash(real_episode_id)), cacheTime=1).xpath('/streams/stream[@compressie_formaat="wmv" and @compressie_kwaliteit="bb"]/streamurl')[0].text.strip()
    except:
      stream = XML.ElementFromURL(STREAM_URL % (real_episode_id, GetHash(real_episode_id)), cacheTime=1).xpath('/streams/stream[@compressie_formaat="wmv" and @compressie_kwaliteit="sb"]/streamurl')[0].text.strip()
  
  return Redirect(WindowsMediaVideoURL(stream))

###################################################################################################
def Thumb(url, alt_url, mimetype='image/jpeg'):
  try:
    data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
    if url[-4:] == '.png':
      mimetype = 'image/png'
    return DataObject(data, mimetype)
  except:
    if alt_url is not None:
      return Thumb(url=alt_url, alt_url=None)
  
  return Redirect(R(ICON))
