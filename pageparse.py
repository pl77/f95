import os
from bs4 import BeautifulSoup, NavigableString
import json
from tqdm import tqdm
from f95_models import db_connect, create_tables, User, Tag, Image, Developer, Platform, Link, Language, Thread, \
    ThreadImage, ThreadLink, ThreadTag
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound


engine = db_connect()
create_tables(engine)
DBSession = sessionmaker(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = DBSession()
    session.expire_on_commit = False
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def parse_html(thread_id, fpath, rawhtml):
    infodict = dict()

    soup = BeautifulSoup(rawhtml, "lxml")
    if soup.title.head == 'Google':
        return None
    # divs = rl.find_all('div')
    try:
        infodict['canonical'] = soup.select_one('link[rel="canonical"]').attrs['href']
    except AttributeError:
        print("AttributeError, canonical:", fpath)
        infodict['canonical'] = None
    try:
        infodict['title'] = soup.head.title.text
    except IndexError:
        print("IndexError, title:", fpath)
        infodict['title'] = None
    infodict['id'] = thread_id
    infodict['details'] = None
    infodict['user_id'] = None
    infodict['user_name'] = None
    infodict['user_url'] = None
    infodict['mainimage'] = None
    infodict['pages'] = None
    infodict['votes'] = None
    infodict['images'] = list()
    infodict['links'] = list()
    infodict['tags'] = list()
    try:
        maincontent = soup.select_one('div[uix_component="MainContent"]')
    except IndexError:
        print('Broken File:', fpath)
        return infodict

    try:
        infodict['title'] = str(maincontent.select_one('h1[class="p-title-value"]').contents[-1]).strip()
    except (IndexError, AttributeError):
        pass
    try:
        voteraw = maincontent.select_one('div[class="tabs tabs--standalone"]').div
        infodict['votes'] = int(voteraw.span.find_all('a')[1].text[9:-1])
    except (IndexError, AttributeError, ValueError):
        pass
    try:
        infodict['pages'] = int(maincontent.select_one(
            'div[class="inputGroup inputGroup--numbers"]').div.input.attrs['max'])
    except (IndexError, AttributeError, ValueError):
        pass
    userchunk = soup.select_one('a[class^="username"]')
    try:
        infodict['user_id'] = int(userchunk.attrs['data-user-id'])
    except (IndexError, AttributeError):
        pass
    try:
        infodict['user_name'] = userchunk.text
    except (IndexError, AttributeError):
        pass
    try:
        infodict['user_url'] = userchunk.attrs['href']
    except (IndexError, AttributeError):
        pass
    try:
        infodict['tags'] = dict()
        tags = maincontent.select('li[class="groupedTags"]')[0].find_all('a')
        for tag in tags:
            tagtitle = tag.text.title()
            uppercasetags = ['2dcg', '3dcg', 'bdsm', 'ntr', 'pov', 'rpg']
            if tagtitle.lower() in uppercasetags:
                tagtitle = tagtitle.upper()
            infodict['tags'][tagtitle] = tag.attrs['href']
    except IndexError:
        pass
    # infodict['author'] = userdate.select('span[class="arg"]')[0].a.text
    try:
        infodict['rating'] = float(maincontent.select_one('select[name="rating"]').attrs['data-initial-rating'])
    except (ValueError, IndexError):
        infodict['rating'] = None
    try:
        infodict['date'] = int(maincontent.select_one('time[class="u-dt"]').attrs['data-time'])
    except (ValueError, IndexError):
        infodict['date'] = None

    mc = maincontent.select_one('div[class="message-content js-messageContent"]')
    try:
        infodict['edited'] = int(mc.select_one('div[class^="message-lastEdit"]').time.attrs['data-time'])
    except (AttributeError, ValueError, IndexError):
        infodict['edited'] = infodict['date']
    mc = mc.select_one('article[class="message-body js-selectToQuote"]')
    infodict['overview'] = list()

    """
    textchunks = mc.text.split('\n')
    for chunk in textchunks:
        if chunk == '' or chunk == ' ':
            continue
        infodict['overview'].append(chunk.strip())
    mcitems = list()
    for mcitem in mc:
        if isinstance(mcitem, NavigableString):
            continue
        elif mcitem.name == 'br':
            continue
        elif mcitem.string is None or mcitem.text.strip() == '':
            continue
        mcitems.append(mcitem)
    """
    textchunks = mc.text.split('\n')
    overview = 0
    lksem = 0
    textkeys = ['overview', 'developer', 'platform', 'censorship', 'language']
    linekeys = ["overview:", "overiew:", "- overview -", "-about-", "overview :", "* game overview", "<plot>",
                "=about=", "about the game:", "about this game collection:", "about this game:", "about the site:",
                "about:", "dev's intro:", "description:", "review:", "welcome:", "from the dev team:", "game info:",
                "game guide:", "story overview: ", "synopsis:", "=speechoice", "synopsis", "description",
                "story gameplay", "the story:", "about this game", "about the game", "basic plot", "plot:", "plot",
                "about", "overview", "story:", "story -", "story"]
    for tk in textkeys:
        infodict[tk] = None
    for chunk in textchunks:
        chunklow = chunk.lower().strip()
        if chunklow == '' or chunklow == ' ':
            pass
        if overview == 0:
            for linekey in linekeys:
                if chunklow.startswith(linekey):
                    lklen = len(linekey) + 1
                    if len(chunklow) > lklen + 1:
                        if isinstance(infodict['overview'], str) and len(infodict['overview']) > 3:
                            infodict['overview'] = f"{infodict['overview']} {chunk[lklen:].strip()}"
                        else:
                            infodict['overview'] = chunk[lklen:].strip()
                        overview = 2
                        lksem = 1
                        break
                    else:
                        overview = 1
                        lksem = 1
                        break
        if lksem == 1:
            lksem = 0
            continue
        if overview == 1:
            if 'developer:' in chunklow:
                if chunklow.startswith('developer:'):
                    infodict['developer'] = chunk[11:].strip()
                    overview = 0
                else:
                    chunklowchunks = chunklow.split('developer:')
                    infodict['developer'] = chunklowchunks[-1]
                    overviewaddition = "developer: ".join([chl for chl in chunklowchunks[:-1]])
                    infodict['overview'] = " ".join([infodict['overview'], overviewaddition])
                    overview = 0
            else:
                if isinstance(infodict['overview'], str) and len(infodict['overview']) > 3:
                    infodict['overview'] = f"{infodict['overview']} {chunk.strip()}"
                else:
                    infodict['overview'] = chunk.strip()
                infodict['overview'] = chunk.strip()
                overview = 2
        elif overview == 2:
            if len(chunk) > 5:
                if 'developer:' in chunklow:
                    if chunklow.startswith('developer:'):
                        infodict['developer'] = chunk[11:].strip()
                    else:
                        chunklowchunks = chunklow.split('developer: ')
                        infodict['developer'] = chunklowchunks[-1]
                        overviewaddition = "developer: ".join([chl for chl in chunklowchunks[:-1]])
                        infodict['overview'] = " ".join([infodict['overview'], overviewaddition])
                else:
                    infodict['overview'] = "{} {}".format(infodict['overview'], chunk.strip())
            overview = 0
        elif chunklow.startswith('developer:'):
            infodict['developer'] = chunk[11:].strip()
        elif chunklow.startswith('platform:'):
            infodict['platform'] = chunk[10:].strip()
        elif chunklow.startswith('censorship:'):
            infodict['censorship'] = chunk[12:].strip()
        elif chunklow.startswith('language:'):
            infodict['language'] = chunk[10:].strip()

    imagelinks = set()
    if infodict['overview'] is None or infodict['overview'] == '' or len(infodict['overview']) < 10:
        broadsearch = mc.select_one('noscript')
        while True:
            if isinstance(broadsearch, NavigableString):
                bt = str(broadsearch).strip()
            else:
                try:
                    bt = broadsearch.text
                except AttributeError:
                    bt = ''
            if bt == '':
                broadsearch = broadsearch.next
            else:
                break
        infodict['overview'] = bt

    try:
        infodict['images'] = list()
        images = mc.select('a[class="js-lbImage"]')
        for image in images:
            imgname = image.img.attrs['alt']
            imgurl = image.attrs['href']
            imgurl = imgurl.replace('/thumb/', '/')
            infodict['images'].append((imgname, imgurl))
            imagelinks.add(imgurl)
    except IndexError:
        pass
    try:
        infodict['downloadlinks'] = list()
        try:
            dlinks = mc.select_one('span[style="font-size: 18px"]').find_all('a')
        except AttributeError:
            dlinks = mc.select('a[class="link link--external"]')
        for dlink in dlinks:
            try:
                downloadlink = dlink.attrs['href']
                if downloadlink not in imagelinks and not downloadlink.startswith('https://f95zone.com/index.php'):
                    infodict['downloadlinks'].append(downloadlink)
            except KeyError:
                continue
    except IndexError:
        pass

    return infodict


def insert_thread(infodict):
    user_name = infodict.pop('user_name')
    user_url = infodict.pop('user_url')
    user_id = infodict.pop('user_id')
    tags = infodict.pop('tags')
    links = infodict.pop('downloadlinks')
    images = infodict.pop('images')
    developer = infodict.pop('developer')
    platform = infodict.pop('platform')
    language = infodict.pop('language')

    with session_scope() as session:
        try:
            user = session.query(User).filter(User.id == user_id).one()
            infodict['user_id'] = user.id
        except NoResultFound:
            user = User(id=user_id, name=user_name, url=user_url)
            session.add(user)
            session.flush()
            infodict['user_id'] = user.id
        tagidlist = list()
        for tag_name, tag_url in tags.items():
            try:
                tag = session.query(Tag).filter(Tag.name == tag_name).one()
                tagidlist.append(tag.id)
            except NoResultFound:
                tag = Tag(name=tag_name, url=tag_url)
                session.add(tag)
                session.flush()
                tagidlist.append(tag.id)
        linkidlist = list()
        for link in links:
            try:
                link = session.query(Link).filter(Link.url == link).one()
                linkidlist.append(link.id)
            except NoResultFound:
                link = Link(url=link)
                session.add(link)
                session.flush()
                linkidlist.append(link.id)
        imageidlist = list()
        for image_name, image_url in images:
            try:
                image = session.query(Image).filter(Image.url == image_url).one()
                imageidlist.append(image.id)
            except NoResultFound:
                image = Image(name=image_name, url=image_url)
                session.add(image)
                session.flush()
                imageidlist.append(image.id)
        try:
            developer = session.query(Developer).filter(Developer.name == developer).one()
            infodict['developer_id'] = developer.id
        except NoResultFound:
            developer = Developer(name=developer)
            session.add(developer)
            session.flush()
            infodict['developer_id'] = developer.id
        try:
            platform = session.query(Platform).filter(Platform.name == platform).one()
            infodict['platform_id'] = platform.id
        except NoResultFound:
            platform = Platform(name=platform)
            session.add(platform)
            session.flush()
            infodict['platform_id'] = platform.id
        try:
            language = session.query(Language).filter(Language.name == language).one()
            infodict['language_id'] = language.id
        except NoResultFound:
            language = Language(name=language)
            session.add(language)
            session.flush()
            infodict['language_id'] = language.id
        try:
            thread = session.query(Thread).filter(Thread.id == infodict['id']).one()
            # if infodict['name'] != '' and thread.name != infodict['name']:
            #     thread.name = infodict['name']
            thread.edited = infodict['edited']
            thread.views = infodict['views']
            thread.votes = infodict['votes']
            thread.likes = infodict['likes']
            thread.pages = infodict['pages']
            thread.version = infodict['version']
            thread.rating = infodict['rating']
            session.flush()
            thread_id = thread.id
        except NoResultFound:
            thread = Thread(**infodict)
            session.add(thread)
            session.flush()
            thread_id = thread.id
        for tag_id in tagidlist:
            try:
                session.query(ThreadTag).filter(ThreadTag.tag_id == tag_id,
                                                ThreadTag.thread_id == thread_id).one()
            except NoResultFound:
                tag_id = ThreadTag(tag_id=tag_id, thread_id=thread_id)
                session.add(tag_id)
                session.flush()
        for link_id in linkidlist:
            try:
                session.query(ThreadLink).filter(ThreadLink.link_id == link_id,
                                                 ThreadLink.thread_id == thread_id).one()
            except NoResultFound:
                link_id = ThreadLink(link_id=link_id, thread_id=thread_id)
                session.add(link_id)
                session.flush()
        for image_id in imageidlist:
            try:
                session.query(ThreadImage).filter(ThreadImage.image_id == image_id,
                                                  ThreadImage.thread_id == thread_id).one()
            except NoResultFound:
                image_id = ThreadImage(image_id=image_id, thread_id=thread_id)
                session.add(image_id)
                session.flush()
        session.commit()


def main():
    jsondict = dict()
    jsondir = os.path.join(os.getcwd(), "JSON")
    for jfile in os.listdir(jsondir):
        jpath = os.path.join(jsondir, jfile)
        with open(jpath, 'r') as jfp:
            jfile = json.load(jfp)
            jdata = jfile['msg']['data']
            for thread in jdata:
                thread_id = thread['thread_id']
                jsondict[thread_id] = thread
    download_dir = r"D:\dazpages\f95"
    # fset = set()
    for root, dirs, files in os.walk(download_dir):
        for file in tqdm(files):
            try:
                thread_id = int(file.split('.')[0].split('-')[1])
            except (IndexError, TypeError):
                print("Type Error for", file)
                continue
            fpath = os.path.join(r"D:\dazpages\f95", file)
            try:
                with open(fpath, 'r', encoding='UTF-8') as tempfile:
                    rawhtml = tempfile.read()
                infodict = parse_html(thread_id, fpath, rawhtml)
            except FileNotFoundError:
                continue
            infodict['title'] = jsondict[thread_id]['title']
            infodict['developer'] = jsondict[thread_id]['developer']
            infodict['version'] = jsondict[thread_id]['version']
            infodict['views'] = jsondict[thread_id]['views']
            infodict['likes'] = jsondict[thread_id]['likes']
            infodict['prefixes'] = jsondict[thread_id]['prefixes']
            infodict['rating'] = jsondict[thread_id]['rating']
            infodict['image_cover'] = jsondict[thread_id]['images']['cover']
            infodict['id'] = thread_id
            insert_thread(infodict)


if __name__ == '__main__':
    # with open('outputjson.json', 'w') as jsonfile:
    #    main(jsonfile)
    main()
