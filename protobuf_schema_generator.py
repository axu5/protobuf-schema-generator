from protobuf_decoder.protobuf_decoder import Parser
import sys
import os

if len(sys.argv) < 2:
  print("STUPID ADD THE HEX INPUT FOLDER >:(")
  quit(1)

PROTO_VERSION = 2

type_mapping = {
  1: "double", # latitude
  # 2: "bytes", # ?
  3: "sint32", # shareExpiration (maybe timestamp)
  4: "uint64",
  5: "string", # action probably wrong
  8: "bool",
  9: "string",
  11: "__CUSTOM_TYPE_BROKEN",
  12: "string", # string until proven innocent (meetingKey)
  13: "uint32", # tcpPort
  14: "enum",
  17: "uint32", # some date thing
}

class Field:
  def __init__(self, data, is_enum=False):
    if PROTO_VERSION == 3 or is_enum:
      self.label = ""
    else:
      self.label = "repeated"
    self.is_enum = is_enum
    self._type_num = -99
    self._type = ""
    self.name = ""
    self._id = -99
    self.default = ""
    self.parse(data)
  
  def parse(self, data):
    for x in data:
      opr = x["field"]
      val = x["data"]
      if opr == 1: # field name
        self.name = val
        pass
      elif opr == 2: # enum field id
        if not isinstance(val, int):
          print("Val is fucked", val, x)
          continue
        self._id = val
        pass
      elif opr == 3: # field id
        if not isinstance(val, int):
          print("Val is fucked", val, x)
          continue
        self._id = val
        pass
      elif opr == 4: # label v2
        if val == 1 and PROTO_VERSION == 2:
          self.label = "optional"
        pass
      elif opr == 5: # type (own mappings)
        if val not in type_mapping:
          print("Shit hit the fan")
          print(self.name)
          print(val)
          quit(1)
        self._type_num = val
        self._type = type_mapping[val]
        pass
      elif opr == 6: # custom message type
        self._type = val.strip(".")
        pass
      elif opr == 7: # unknown doesn't exist
        self.default = val
        if PROTO_VERSION == 2:
          self.label = "optional"
        pass
      # elif opr == 8: # unknown doesn't exist
        # pass
      elif opr == 9: # unknown exists (usually 0?)
        if val != 0:
          print("WTFF FIELD 9 NOT 0:\t", val)
      else:
        print("UNKNOWN FIELD NUM", opr, val)

class Message:
  def __init__(self, data, is_enum=False):
    self.name = ""
    self.is_enum = is_enum
    self.fields = []
    self.sub_types = []
    self.parse(data)
  
  def parse(self, data):
    for field in data:
      field_num = field["field"]

      if field_num == 1: # Message name
        message_name = field["data"]
        self.name = message_name
      elif field_num == 2: # Field for Message
        field_data = field["data"]["results"]
        field = Field(field_data, is_enum=self.is_enum)
        self.fields.append(field)
      elif field_num == 3: # Sub message
        field_data = field["data"]["results"]
        new_enum = Message(field_data)
        self.sub_types.append(new_enum)
      elif field_num == 4: # Enum
        field_data = field["data"]["results"]
        new_enum = Message(field_data, is_enum=True)
        self.sub_types.append(new_enum)
      elif field_num == 8: # Action/content
        pass
      else:
        print("UNKNOWN MESSAGE FIELD", field)

  def to_str(self,indentation_count=0):
    ind = "  "
    out = ""
    if indentation_count > 0:
      out += "\n\n"
    out += f"{ind*indentation_count}{'enum' if self.is_enum else 'message'} {self.name}\n"
    out += ind*indentation_count + "{\n"
    for field in self.fields:
      out += f"{ind*(indentation_count+1)}{field.label} {field._type} {field.name} = {field._id}"
      if field.default != "" and PROTO_VERSION == 2:
        if field._type == "string":
          out += f' [default = "{field.default}"]'
        elif not field._type in list(type_mapping.values()):
          # out += f' [default = {field._type}.{field.default}]'
          out += f' [default = {field.default}]'
        else:
          out += f' [default = {field.default}]'
      out += ";\n"
    for sub_type in self.sub_types:
      out += sub_type.to_str(indentation_count=indentation_count+1) + "\n"
    out += ind*indentation_count + "}"
    return out

class File:
  def __init__(self, data):
    self.name = ""
    self.package = "" 
    self.imports = []
    self.messages = []
    self.parse(data)
  
  def parse(self, data):
    for f in data:
      field_num = f["field"]
      field_data = f["data"]

      if field_num == 1:
        self.name = field_data
      elif field_num == 3:
        self.imports.append(field_data)
      elif field_num == 4:
        new_message = Message(field_data["results"])
        self.messages.append(new_message)
      elif field_num == 5:
        new_enum = Message(field_data["results"], is_enum=True)
        self.messages.append(new_enum)
      elif field_num == 8:
        self.package = field_data["results"][0]["data"]
  
  def to_str(self):
    output = f'syntax = "proto{PROTO_VERSION}";\n'
    if self.package != "":
      output += f'package {self.package};\n'
    for imp in self.imports:
      output += f'import "{imp}";\n'
    output += "\n"
    for msg in self.messages:
      output += msg.to_str() + "\n\n"
    return output

imports = []
for file in os.listdir(sys.argv[1]):
  print("parsing\t", file)
  f = open(sys.argv[1] + "/" + file, "r")
  data = f.read()

  obj = Parser().parse(data).to_dict()
  we_care_about = obj["results"]

  final = File(we_care_about)
  imports.append(final.imports)

  if final.name == "":
    print("Error parsing\t", file)
    continue

  output = final.to_str()

  of = open("./output/" + final.name, "w")
  of.write(output)

  f.close()
  of.close()

for importz in imports:
  for imp in importz:
    if not os.path.isfile("./output/" + imp):
      print("MISSING IMPORT FOUND\t", imp)

print("OK")