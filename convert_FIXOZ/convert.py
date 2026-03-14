import argparse
import os
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from bs4.formatter import XMLFormatter


# -------------------------------------------------------------------------------

class SortAttributes(XMLFormatter):
    def attributes(self, tag):
        """Reorder a tag's attributes however you want."""
        attr_order = ['appField', 'fixField', 'default', 'msgType', 'precision', 'offset', 'disable']
        new_order = []
        for element in attr_order:
            if element in tag.attrs:
                new_order.append((element, tag[element]))
        for pair in tag.attrs.items():
            if pair not in new_order:
                new_order.append(pair)
        return new_order


# -------------------------------------------------------------------------------

def convert_xml(filename, assoc):
    with open(filename, 'r') as f:
        file = f.read()

    soup = BeautifulSoup(file, 'xml')
    successfull_build = True

    fix_field_tag = soup.find("fix_fields")

    if (fix_field_tag):
        fix_field_tag.name = "to_fix"
        for tf_field in fix_field_tag:
            if tf_field.name is None or tf_field.name == "field":
                continue
            tf_field["fixField"] = tf_field.name
            tf_field.name = "field"

    fields_tag = soup.find("fields")

    for field in fields_tag.children:
        if field.name is None:
            continue
        if field.name != "field":
            field["appField"] = field.name
            field.name = "field"

        fixFieldAttrValue = field.get('fixField')

        if fixFieldAttrValue is not None and not fixFieldAttrValue.isdigit():
            if fixFieldAttrValue in assoc:
                field["fixField"] = assoc[fixFieldAttrValue]
            else:
                successfull_build = False
                try:
                    raise LookupError("fixField [{}] wasn't found in the spec files you specified".format(field["fixField"]))
                except LookupError as e:
                    print(e)


    if (not successfull_build):
        return;

    result = soup.prettify("utf-8", formatter=SortAttributes()).decode()

    with open(filename, 'w') as f:
        f.write(result)


# -------------------------------------------------------------------------------

def create_associations(xml_file):
    associations = {}

    tree = ET.parse(xml_file)
    root = tree.getroot()

    field_tags = root.findall(".//field")

    for field_tag in field_tags:
        number = field_tag.get("number")
        name = field_tag.get("name")
        if number and name:
            associations[name] = int(number)

    return associations


# -------------------------------------------------------------------------------

def parse_xml_files_in_folder(folder_path):
    all_associations = {}

    for filename in os.listdir(folder_path):
        if filename.endswith(".xml"):
            file_path = os.path.join(folder_path, filename)
            associations = create_associations(file_path)
            all_associations.update(associations)

    return all_associations


# -------------------------------------------------------------------------------
# -------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse spec files in the given folder and create associations between tag names and numbers.")
    parser.add_argument("spec_folder_path", help="Path to the folder containing spec files")
    parser.add_argument("fields_file", help="Path to the PLUGIN_fields.xml file to convert")

    args = parser.parse_args()
    associations = parse_xml_files_in_folder(args.spec_folder_path)

    convert_xml(args.fields_file, associations)


if __name__ == "__main__":
    main()

# -------------------------------------------------------------------------------
