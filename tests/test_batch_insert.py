
import urllib


if __name__ == '__main__':
    for i in range(1000000):
        postdata = urllib.urlencode({'project':'a', 'spider':'b', 'url':'%s' % i})
        r=urllib.urlopen('http://localhost:8889/visited/a/', postdata)
        r.read()