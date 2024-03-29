#! /usr/bin/env python

import re, sys, sched, datetime, urllib, urllib2, urlparse
import time as timeModule
from datetime import datetime,date,timedelta,time
from pytz import timezone,utc
import os, platform, getopt

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from multiprocessing import Process as Thread

dictCode = {}
fname = "Airport_TZ.info"

with open(fname) as f:
    content = f.read().splitlines()

for line in content:
   val = line.split('\t')
   dictCode[val[0]] = val[1]

#print dictCode
utc = timezone('UTC')

def is_dst (tzone):
    """Determine whether or not Daylight Savings Time (DST)
    is currently in effect"""
    x = datetime(datetime.now().year, 1, 1, 0, 0, 0, tzinfo=timezone(tzone)) # Jan 1 of this year
    y = datetime.now(timezone(tzone))
    # if DST is in effect, their offsets will be different
    return not (y.utcoffset() == x.utcoffset())


def find_times(firstName, lastName, confirmation):
   baseUrl = 'https://www.southwest.com'
   infoUrl = '/flight/view-air-reservation.html?confirmationNumberFirstName='+firstName+'&confirmationNumberLastName='+lastName+'&confirmationNumber='+confirmation
   retrieveUrl = urlparse.urljoin(baseUrl, infoUrl)
   print(retrieveUrl)

   browser = webdriver.Firefox()
   browser.get(retrieveUrl)
   html = browser.page_source
   timeModule.sleep(10)

   flightSegments  = browser.find_elements_by_class_name('checkout-flight-detail')
   print("Found Segments ", len(flightSegments))
   retval=[]
   for fSegment in flightSegments:
      fdate = fSegment.find_elements_by_class_name('flight-detail--heading-date')[0].text.split(' ')[0].split('/')
      ftime = fSegment.find_elements_by_class_name('time--value')[0].text
      ft = ftime[:-2].split(':')
      if ftime[-2:] == "PM":
         ft[0] = int(ft[0]) + 12

      fCode = fSegment.find_elements_by_class_name('flight-segments--airport-code')[0].text

      fDateTime = datetime(int('20' + fdate[2]), int(fdate[0]), int(fdate[1]), int(ft[0]), int(ft[1]), 0, 0, tzinfo=timezone(dictCode[fCode]))

      #print (fdate, ftime, fCode, fDateTime)
      retval.append([fDateTime, fdate, ftime, fCode])


   print retval
   browser.quit()
   return retval



def auto_checkin(firstName, lastName, confirmation, flightDateTime=None, phone = None):

   baseUrl = 'https://www.southwest.com'
   dataUrl = '/flight/retrieveCheckinDoc.html?firstName='+firstName+'&lastName='+lastName+'&confirmationNumber='+confirmation
   checkinUrl = urlparse.urljoin(baseUrl, dataUrl)
   print(checkinUrl)

   waitTime = flightDateTime - utc.localize(datetime.utcnow())

   if waitTime.total_seconds() < 0:
      print "\n\n\nThis flight seems to have already left... Not checking in\n\n\n"
      return

   #waitTime = waitTime - timedelta(days=1)
   #print waitTime

   #wtime = waitTime.total_seconds()
   #print("Waiting for ", wtime, "time", waitTime)

   # Launch Firefox GUI
   checkinTime = flightDateTime - timedelta(days=1)
   wtime = (checkinTime - utc.localize(datetime.utcnow())).total_seconds()
   while (wtime > 20):
      wtime = (checkinTime - utc.localize(datetime.utcnow())).total_seconds()
      timeModule.sleep(10)
      wdays = int(wtime/60/60/24)
      whours = int((wtime - wdays*60*60*24)/60/60)
      wmins = int((wtime - wdays*60*60*24 - whours*60*60)/60)
      wsecs = int(wtime - wdays*60*60*24 - whours*60*60 - wmins*60)
      print 'Waiting to check in for ',  wdays, " Days ", whours, " Hours ", wmins, " Minutes ", wsecs, " Seconds "
      #timeModule.sleep(waitTime.total_seconds()-1)

   print("Time to Checkin ...", checkinUrl)

   loop = True
   browser = webdriver.Firefox()
   timeModule.sleep(10)
   browser.get(checkinUrl)
   html = browser.page_source

   while loop:

      print ("Sleeping 10 Seconds ...")
      timeModule.sleep(10)

      try: 
         err = browser.find_element_by_class_name('error-reservation-not-found')
         print("Found Element Error ", err)
      except:
         print("No Error Found: Success at ", datetime.now())
         loop = False

      button = browser.find_element_by_class_name('submit-button')
      button.click()
      timeModule.sleep(10)
      html = browser.page_source

   ## Print boarding Position
   #class: air-check-in-passenger-item--information-boarding-position
   #sub-class: swa-g-screen-reader
   #.text of that gets the "Boarding Position B59"
   
   #bp = browser.find_element_by_class_name('air-check-in-passenger-item--information-boarding-position')
   #bpt = bp.find_element_by_class_name('swa-g-screen-reader-only')
   #print ("\n\n\n *** Your Boarding Position is ", bpt.text)   
   #print ("\n\n\n *** Your Boarding Position is ", bpt.get_attribute('value'))

   ## Text the boarding pass
   if phone:
      try:
         phBtn = browser.find_element_by_class_name('boarding-pass-options--button-text')
         phBtn.click()
         inp1 = browser.find_element_by_xpath('//*[@id="textBoardingPass"]')
         inp1.click()
         inp1.send_keys(phone)
         timeModule.sleep(10)
         #button = browser.find_element_by_class_name('submit-button')
         button = browser.find_element_by_xpath('//*[@id="form-mixin--submit-button"]')
         button.click()
      except:
         print("wierd error -- No Text For You -- ")

   timeModule.sleep(10)
   browser.quit()


def main(argv):

   firstName = ''
   lastName = ''
   confirmation = ''
   phone = None

   try:
      opts, args = getopt.getopt(argv,"hf:l:c:p:",["fname=","lname=","confirmation=","phone="])
   except getopt.GetoptError:
      print 'auto_checkin.py -f <firstName> -l <lastName> -c <confirmation> -p <phone>'
      sys.exit(2)

   for opt, arg in opts:
      if opt == '-h':
         print 'auto_checkin.py -f <firstName> -l <lastName> -c <confirmation> -p <phone>'
         sys.exit()
      elif opt in ("-f", "--fname"):
         firstName = arg
      elif opt in ("-l", "--lname"):
         lastName = arg
      elif opt in ("-c", "--confirmation"):
         confirmation = arg
      elif opt in ("-p", "--phone"):
         phone = arg

   time = 1000000

   if platform.system() == 'Darwin': # MACOS needs caffienate
      t1 = Thread(target=doCheckIn,args=(firstName,lastName,confirmation,phone,))
      t2 = Thread(target=runCaffeinate,args=(time,))

      t1.start()
      t2.start()

      print("Waiting to join")
      t1.join()
      t2.terminate()
      print("Finished Thread1")

   else:
      doCheckIn(firstName,lastName,confirmation,phone)

def runCaffeinate(time):
   os.system('caffeinate -t 0')

def doCheckIn(firstName,lastName,confirmation,phone):

   flightinfo = find_times(firstName, lastName, confirmation)
   for flight in flightinfo:
      if is_dst(dictCode[flight[3]]):
         flight[0] = flight[0] - timedelta(hours=1)      
      auto_checkin(firstName, lastName, confirmation, flight[0], phone)

   
if __name__ == '__main__':
   main(sys.argv[1:])
