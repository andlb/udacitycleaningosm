import csv
import codecs
import xml.etree.cElementTree as ET

# List values match the fields from the table.
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



def shape_element_node(element, 
                  node_attr_fields=NODE_FIELDS):

    """
    Shape tag element "node" to write its content in a file.

    Args:
      element (obj): is a element from the xml file.
      node_attr_fields (list, optional) is a list with the name of 
        each property from the table node. Default to NODE_FIELDS list
    
    Returns:
      dict: a dictionary indexed by node and node_tags key.
        The value for node key is a dictionary 
          which has as key the name of node table property and the value 
          is the content from the xml element

        The value for node_tags key is a list of dictionaries, 
          and each dictionary has as key the nodes_tags property name and the value is the 
          content from xml element.
    """

    node_attribs = {}
    tags = []            

    node_attribs = getNodeAndWay(element,node_attr_fields)   
    tags = getTag(element)
    return {'node': node_attribs, 'node_tags': tags}


def shape_element_way(element,                
                  way_attr_fields=WAY_FIELDS):
    """
    Shape tag element "way" to write its content in a file.

    Args:
      element (obj): is a element from the xml file.
      way_attr_fields (list, optional): is a list with the name of 
        each property from the table way. Default to WAY_FIELDS list
    
    Returns:
     dict: A dictionary indexed by way, way_nodes and way_tags key.
      The value for way key is a dictionary 
        which has as key the name of way table property and the value 
        is the content from the xml element
        
      The value for way_nodes key is a list of dictionaries, 
        and each dictionary has as key the way_nodes property name and the value is the 
        content from xml element.

      The value for way_tags key is a list of dictionaries, 
        and each dictionary has as key the way_tags property name and the value is the 
        content from xml element.
    """
    
    way_attribs = {}
    way_nodes = []
    tags = []

    way_attribs = getNodeAndWay(element,way_attr_fields)                  
    way_nodes = getWayNode(element)
    tags = getTag(element)
    return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


def getNodeAndWay(element,array):
  """
  Create a dictionary where the key is the name of the table and the value is the content of the element.

  Args:
    element(obj): content from the element file.
    array(dict): is the property name of the table. It can be a node or a way table

  Returns:
    dict: A dictionary with the way or node table fields value"""  
  t_attribs = {}
  for atr in array:
    if atr in element.attrib:
      t_attribs[atr] = element.attrib[atr]
  return t_attribs

def getTag(element):
  """ 
  Create a list of dictionary and for each dictionary 
    the key is the name of the table and the value is the content of the element.

  Args:
    element (obj): content from the element file.

  Returns:
    dict: A list of dictionary with the tag table fields value """
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
  """ 
  Create a list of dictionaries and for each dictionary 
    the key is the name of the table and the value is the content of the element.

  Args:
    element(obj): content from the element file.
  
  Returns:
    list: A list of dictionary with the "way node" table fields value 
  """

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


def audity_street(street):
  """
    Verify if the street name is correct.
    
    Args:
      street (str): street name

    Returns:
      bool: True if the start part of the street name is in the expectedStreet list, 
          else, return False.
  """
  street = street.split(' ')
  if street[0] in expectedStreet:
    return True
  return False
    

def audityandfix(street,diction=STREETS,mapstreet=MAPSTREET):
  """
    Fix the street abbreviation or write a list of errors.

    Args:
      street (str): street name
      diction (list, optional): is a list with the correct 
        start street name. Default to STREETS dictionary
      mapstreet (dict, optional): is a dictionary and its key is the wrong start street name value 
        and its value is the correct. Default to MAPSTREET dictionary
    
    Returns:
      str: When is possible to fix it will return
        a string with the street name starting with one of the value of expectedStreet list. 
        Else, it will return the street parameter value with the first letter in uppercase.
      
  """
  ret = street
  lstreet = ret.split(" ")
  lstreet[0] = lstreet[0].replace('.','').title()
  if lstreet[0] in mapstreet:
    lstreet[0] = mapstreet[lstreet[0]]
  ret = " ".join(lstreet)
  if not audity_street(ret):
    if not lstreet[0] in diction:
      diction[lstreet[0]] = 1
    else:
      diction[lstreet[0]] = diction[lstreet[0]] + 1  
  return ret
      

def is_street(street):
  """ 
  Verify if the element has the street name.
  
  Args:
    street(str): tag value is being read.

  Returns:
    bool: True if it is reading a street tag, else false  
  """
  if street  == "street":
    return True
  else:
    return False

def is_postalcode(tag):
  """   
  Verify if the element has the postal code.
  
  Args:
    tag(str): tag value is being read.

  Returns:
    bool: True if it is reading a postal code tag, else false
  """
  if tag == "postcode":
    return True
  return False  

def auditory_postalcode(postalcode):
  """
  Verify if the postal code follow the brazilian pattern.

  Args:
    postalcode (str): value of the element when it is a postal code type.

  Returns:
     bool: False when the post code doesn't follow the brazilian pattern, else true
  """

  ret = True
  postcode = postalcode.split('-')
  if len(postcode) < 2:
    ret = False
  else:
    if len(postcode[0])!=5:
      ret = False
    if len(postcode[1])!=3:
      ret = False
  return ret

def fix_postalcode(postalcode):
  """  
  Fix the postal code when it doesn't have the dash or when it doesn't have -000 in the end 

  Args:
    postalcode (str): value of the element when it is a postal code type.

  Returns:
    str: a string with the postal code when it is possible to fix or None when it is not

  """  
  if len(postalcode) == 8 or len(postalcode) == 5:
    if len(postalcode) == 8:
      nvalue = postalcode[0:5] +'-'+postalcode[5:] 
    elif len(postalcode) == 5:
      nvalue = postalcode[0:] + "-000"
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
  """
  Transform the dictionary values in list.

  Args:
    t_dictionary (dict). Dictionary content to change it to list.

  Returns:
    list: an list based on a dictionary value """  
  return [w for w in t_dictionary.values()]

# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file):
  """
  Processing each XML element and write to csv(s)

  Args:
    file(str): a string with the path and the name of the file. 
  """  

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
      
      #writing the rows in every file according the tag.
      if element.tag == 'node':
        el = shape_element_node(element)
        wNode.writerow(listtoarray(el['node']))
        for lista in el['node_tags']:
          wNodeTag.writerow(listtoarray(lista))        
      elif element.tag == 'way':
        el = shape_element_way(element)
        wWay.writerow(listtoarray(el['way']))
        for lista in el['way_nodes']:
          wWayNode.writerow(listtoarray(lista))
        for lista in el['way_tags']:          
          wWayTag.writerow(listtoarray(lista))                  


if __name__ == '__main__':
  process_map(OSM_PATH)
  print(STREETS)