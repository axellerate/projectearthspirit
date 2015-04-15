import urllib2

NumberOfCars = 36034

index = 1

for i in range(1, NumberOfCars):
    url = "http://fueleconomy.gov/ws/rest/vehicle/%s" %str(i)
    xml = urllib2.urlopen(url).read()
    
    carId = i
    
    start = xml.find("<make>")+6
    end = xml.find("</make>")
    make = xml[start:end]

    start = xml.find("<model>")+7
    end = xml.find("</model>")
    model = xml[start:end]

    start = xml.find("<year>")+6
    end = xml.find("</year>")
    year = xml[start:end]
    
    start = xml.find("<co2TailpipeGpm>")+16
    end = xml.find("</co2TailpipeGpm>")
    emissions = float(xml[start:end])
    
    print make + " " + model + " " + year + " " + str(emissions)
