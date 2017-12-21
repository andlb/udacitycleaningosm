import csv
import codecs
import xml.etree.cElementTree as ET

# Array values match the fields from the table.
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

# CSV file name to be imported to the database.
NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

STREETS={}
POSTCODEERROR=[]

expectedStreet = ["Rua", 
                  "Avenida", "Praça", "Largo", 
                  "Ladeira", "Via","Viaduto", "Travessa", 
                  "Parque", "Alameda",
                  "Vila",
                  "Rodovia",
                  "Estrada"]

MAPSTREET = {
  "Av":"Avenida",
  "Estr":"Estrada",
  "Pç":"Praça",
  "Al":"Alameda",
  "Alamedas":"Alameda",
  "Rue":"Rua",
  "Rúa":"Rua",
  "R":"Rua"
}

# Map file name
OSM_PATH = "SaoPaulo.osm"

# ================================================== #
#               Helper Functions                     #
# ================================================== #



def shape_element(element, 
                  node_attr_fields=NODE_FIELDS,                   
                  way_attr_fields=WAY_FIELDS):
    """Return an dictionary to write the csv file"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []
    if element.tag == 'node':      
      node_attribs = getNodeAndWay(element,node_attr_fields)   
      tags = getTag(element)
      return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
      way_attribs = getNodeAndWay(element,way_attr_fields)                  
      way_nodes = getWayNode(element)
      tags = getTag(element)
      return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}

def getNodeAndWay(element,array):
  """Return a dictionary with the way or node table fields value"""  
  t_attribs = {}
  for atr in array:
    if atr in element.attrib:
      t_attribs[atr] = element.attrib[atr]
  return t_attribs

def getTag(element):
  """ return a array of dictionary with the tag table fields value """
  tags = []
  for etag in element.iter("tag"):    
    if 'k' in etag.attrib:
      kvalue = etag.attrib['k']
      value = etag.attrib['v']
      tipo = "regular"
      # split by ":" when k value is like addr:street. add->key and street->value
      lkvalue = kvalue.split(":")
      if len(lkvalue) > 1:
        tipo = lkvalue[0]
        kvalue = ":".join(lkvalue[1:])
        #fix problems with values abbreviation and type (address = addr)
        if is_street(kvalue):
          if not audity_street(value):
            value = audityandfix(value)
        if is_postalcode(kvalue):        
          if auditory_postalcode(value) == False:          
            value = fix_postalcode(value)
            if value == None:              
              continue
        if tipo == "address":
            tipo = "addr"
      nodetag={}              
      nodetag['id'] = element.attrib['id']
      nodetag['key'] = kvalue
      nodetag['value'] = value
      nodetag['type'] = tipo
      tags.append(nodetag)
  return tags

def getWayNode(element):
  """ return a array of dictionary with the "way node" table fields value """
  way_nodes = []
  position = 0  
  for t in element.iter("nd"):
    waynode = {}
    waynode["id"] = element.attrib['id']
    waynode["node_id"] = t.attrib['ref']
    waynode["position"] = position
    position += 1
    way_nodes.append(waynode)
  return way_nodes


def audity_street(value):
  """Push the first part of the street name in an array"""
  street = value.split(' ')
  if not street[0] in expectedStreet:
    return False
  return False
    

def audityandfix(value,diction=STREETS,mapstreet=MAPSTREET):
  """Fix the street abbreviation or errors"""
  ret = value
  street = ret.split(" ")
  street[0] = street[0].replace('.','').title()
  if street[0] in mapstreet:
    street[0] = mapstreet[street[0]]
  ret = " ".join(street)
  if not audity_street(ret):
    if not street[0] in diction:
      diction[street[0]] = 1
    else:
      diction[street[0]] = diction[street[0]] + 1  
  return ret
      

def is_street(value):
  """ Return True if the it is reading a street tag, else false"""
  if value == "street":
    return True
  else:
    return False

def is_postalcode(value):
  """ Return True if the it is reading a postal code tag, else false"""
  if value == "postcode":
    return True
  return False  

def auditory_postalcode(value):
  """return false when the post code doesn't follow the brazilian pattern"""
  ret = True
  postcode = value.split('-')
  if len(postcode) < 2:
    ret = False
  else:
    if len(postcode[0])!=5:
      ret = False
    if len(postcode[1])!=3:
      ret = False
  return ret

def fix_postalcode(value):
  """Return the postal code when it is possible to fix or None when it is not"""  
  if len(value) == 8:
    nvalue = value[0:5] +'-'+value[5:] 
    # verify if the new code is valid
    if auditory_postalcode(nvalue):
      return nvalue
    else:
      return None
  else:
    return None


def get_element(osm_file, tags=('node', 'way', 'relation')):
  """Yield element if it is the right type of tag"""

  context = ET.iterparse(osm_file, events=('start', 'end'))
  _, root = next(context)
  for event, elem in context:
      if event == 'end' and elem.tag in tags:
          yield elem
          root.clear()


def listtoarray(t_dictionary):
  """Return an array based on a dictionary """  
  return [w for w in t_dictionary.values()]

# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file):
  """Processing each XML element and write to csv(s)"""  

  with codecs.open(NODES_PATH, 'w', "utf-8-sig") as nodes_file, \
    codecs.open(NODE_TAGS_PATH, 'w', "utf-8-sig") as nodes_tags_file, \
    codecs.open(WAYS_PATH, 'w', "utf-8-sig") as ways_file, \
    codecs.open(WAY_NODES_PATH, 'w', "utf-8-sig") as way_nodes_file, \
    codecs.open(WAY_TAGS_PATH, 'w', "utf-8-sig") as way_tags_file:

    wNode = csv.writer(nodes_file, delimiter=';')
    wNodeTag = csv.writer(nodes_tags_file, delimiter=';')
    wWay = csv.writer(ways_file, delimiter=';')
    wWayNode = csv.writer(way_nodes_file, delimiter=';')
    wWayTag = csv.writer(way_tags_file, delimiter=';')
    
    #writing csv file headers
    wNode.writerow(NODE_FIELDS)
    wNodeTag.writerow(NODE_TAGS_FIELDS)
    wWay.writerow(WAY_FIELDS)
    wWayNode.writerow(WAY_NODES_FIELDS)
    wWayTag.writerow(WAY_TAGS_FIELDS)      
    for element in get_element(file, tags=('node', 'way')):
      el = shape_element(element)
      #writing the rows in every file according the tag.
      if element.tag == 'node':
        wNode.writerow(listtoarray(el['node']))
        for lista in el['node_tags']:
          wNodeTag.writerow(listtoarray(lista))        
      elif element.tag == 'way':
        wWay.writerow(listtoarray(el['way']))
        for lista in el['way_nodes']:
          wWayNode.writerow(listtoarray(lista))
        for lista in el['way_tags']:          
          wWayTag.writerow(listtoarray(lista))                  


if __name__ == '__main__':
  process_map(OSM_PATH)
  print(STREETS)

