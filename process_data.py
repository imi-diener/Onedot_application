import pandas as pd
import sys
import copy

source = sys.argv[1]
output_file = sys.argv[2]
s = pd.read_json(source, lines=True)

# Step 1: preprocess data to get one row per sample
# Some values are the same over all rows of a sample and in these cases the fist one can be used.
# many values, however, are stored in the attributes columns, which is why I will loop over them and create new columns
# for each attribute, so that there can be only one row per sample.

preprocessed = pd.DataFrame(index = range(1, max(s["ID"])+1), columns=["ID", "MakeText", "TypeName",
                                                                       "TypeNameFull", "ModelText", "ModelTypeText"])
for i in range(1, max(s["ID"])+1):
    car_id = s[s["ID"] == i]

    preprocessed.loc[i, "ID"] = car_id["ID"].iloc[0]

    preprocessed.loc[i, "MakeText"] = car_id["MakeText"].iloc[0]

    preprocessed.loc[i, "TypeName"] = car_id["TypeName"].iloc[0]

    preprocessed.loc[i, "TypeNameFull"] = car_id["TypeNameFull"].iloc[0]

    preprocessed.loc[i, "ModelText"] = car_id["ModelText"].iloc[0]

    preprocessed.loc[i, "ModelTypeText"] = car_id["ModelTypeText"].iloc[0]

    for attribute in car_id["Attribute Names"]:
        preprocessed.loc[i, attribute] = car_id.loc[car_id["Attribute Names"] == attribute, "Attribute Values"].iloc[0]

# Step 2: normalize data

normalized = copy.deepcopy(preprocessed)

# loop over all samples and normalize values if necessary by transforming them to the target format
for i in range(1, max(s["ID"])+1):

    # normalize condition
    # the schema used here is Occasion=Used, Oldtimer=Restored, Neu=New, Vorführmodell=Original Condition
    # To be sure about this, I would check with the supplier / customer
    if preprocessed.loc[i, "ConditionTypeText"] == "Occasion":
        normalized.loc[i, "ConditionTypeText"] = "Used"
    elif preprocessed.loc[i, "ConditionTypeText"] == "Oldtimer":
        normalized.loc[i, "ConditionTypeText"] = "Restored"
    elif preprocessed.loc[i, "ConditionTypeText"] == "Neu":
        normalized.loc[i, "ConditionTypeText"] = "New"
    elif preprocessed.loc[i, "ConditionTypeText"] == "Vorführmodell":
        normalized.loc[i, "ConditionTypeText"] = "Original Condition"

    # introduce fuel consumption column
    # This column should be populated by the measures that are used in the ConsumptionTotalText field,
    # normalized to the target format. Assuming that the possible formats used are l/100km, km/l
    # or miles per gallon (MPG), i can just look at the last characters in the string
    # this would have to be checked with the supplier / customer.
    try:
        consumption = preprocessed.loc[i, "ConsumptionTotalText"]
        if consumption[-2:] == "km":
            normalized.loc[i, "fuel_consumption_unit"] = "l_km_consumption"
        elif consumption[-1:] == "l":
            normalized.loc[i, "fuel_consumption_unit"] = "km_l_consumption"
        else:
            normalized.loc[i, "fuel_consumption_unit"] = "mi_g_consumption"
    except:
        normalized.loc[i, "fuel_consumption_unit"] = "null"

    # normalize mileage
    # Mileage is given in integers in the source but needs to be a float rounded to one decimal.
    # this can simply be achieved by converting the integers to floats.
    # this is also assuming that the fuel consumption Attribute Name will always be "Km". This is unlikely in the event that
    # there are cars using a different measurement. Thus, I would clarify this beforehand.
    try:
        # I convert it to a string so that the  '.0' will actually be written in the output.
        normalized.loc[i, "mileage"] = str(float(preprocessed.loc[i, "Km"]))
    except:
        normalized.loc[i, "mileage"] = "null"

    # the color has a capital letter at the beginning in the target format, so it needs to be adjusted
    try:
        normalized.loc[i, "color"] = preprocessed.loc[i, "BodyColorText"].capitalize()
    except:
        normalized.loc[i, "color"] = "null"

    # the car body times are named differently, so they need to be adjusted aswell. I will only use terms that are used in the target,
    # although there might be terms referring to specific types (like pick-up), which are not listed in the file.
    # this can simultaniously be used to tell if the type is a car, as there is no value for motorcycles. It could be that certain
    # vehicle types are called differently (truck, for example), but this cannot be inferred from the file's contents.

    if preprocessed.loc[i, "BodyTypeText"] == "Limousine":
        normalized.loc[i, "carType"] = "Saloon"
        normalized.loc[i, "type"] = "car"
    elif preprocessed.loc[i, "BodyTypeText"] == "Kombi":
        normalized.loc[i, "carType"] = "Station Wagon"
        normalized.loc[i, "type"] = "car"
    elif preprocessed.loc[i, "BodyTypeText"] == "Coupé":
        normalized.loc[i, "carType"] = "Coupé"
        normalized.loc[i, "type"] = "car"
    elif preprocessed.loc[i, "BodyTypeText"] == "SUV / Geländewagen":
        normalized.loc[i, "carType"] = "SUV"
        normalized.loc[i, "type"] = "car"
    elif preprocessed.loc[i, "BodyTypeText"] == "Cabriolet":
        normalized.loc[i, "carType"] = "Convertible / Roadster"
        normalized.loc[i, "type"] = "car"
    elif preprocessed.loc[i, "BodyTypeText"] == "Wohnkabine" or preprocessed.loc[i, "BodyTypeText"] == "Kleinwagen" \
            or preprocessed.loc[i, "BodyTypeText"] == "Kompaktvan / Minivan"\
            or preprocessed.loc[i, "BodyTypeText"] == "Sattelschlepper" or preprocessed.loc[i, "BodyTypeText"] == "Pick-up":
        normalized.loc[i, "carType"] = "Other"
        normalized.loc[i, "type"] = "car"
    else:
        normalized.loc[i, "carType"] = "Other"
        normalized.loc[i, "type"] = "motorcycle"

    # I hope these four normalization steps give you an idea of how I tackle such a problem

# Step 3: Integration of the normalized data into the target data schema

output = pd.DataFrame(index=range(1, max(s["ID"])+1), columns=["carType","color","condition","currency","drive","city","country",
                               "make","manufacture_year","mileage","mileage_unit","model","model_variant","price_on_request",
                                                               "type","zip","manufacture_month","fuel_consumption_unit"])


# loop over all samples and fill all fields that are required in the target schema
for i in range(1, max(s["ID"])+1):

    output.loc[i, "carType"] = normalized.loc[i, "carType"]

    output.loc[i, "color"] = normalized.loc[i, "color"]

    output.loc[i, "condition"] = normalized.loc[i, "ConditionTypeText"]

    output.loc[i, "currency"] = "null" # there is no information on this in the source

    output.loc[i, "drive"] = "null" # there is no information on this either

    output.loc[i, "city"] = normalized.loc[i, "City"]

    output.loc[i, "country"] = "CH" # As all cities present are in Switzerland, I insert 'CH' for all samples.
                                    # This might be incorrect for new data and should be clarified with the customer / supplier.
    output.loc[i, "make"] = normalized.loc[i, "MakeText"]

    output.loc[i, "manufacture_year"] = normalized.loc[i, "FirstRegYear"] # This is most likely incorrect, as a car does not necessarily have to be registered
                                                                            # for the first time in the year it was manufactured. I only include this for the sake of completeness.
    output.loc[i, "mileage"] = normalized.loc[i, "mileage"]

    output.loc[i, "mileage_unit"] = "kilometer" # as the attribute name is Km, they are all measured in Kms.
                                                # This ties back in with the issue raised in the normalization step for mileage.

    output.loc[i, "model"] = normalized.loc[i, "ModelText"]

    output.loc[i, "model_variant"] = normalized.loc[i, "ModelTypeText"]

    output.loc[i, "price_on_request"] = "null" # There is no information on this in the source and thus should be clarified aswell.

    output.loc[i, "type"] = normalized.loc[i, "type"]

    output.loc[i, "zip"] = "null" # Again, no information in the source

    output.loc[i, "manufacture_month"] = normalized.loc[i, "FirstRegMonth"] # Same issue with registration month != manufacture month, just for completeness

    output.loc[i, "fuel_consumption_unit"] = normalized.loc[i, "fuel_consumption_unit"]

# Safe the excel file with each step as a seperate sheet
with pd.ExcelWriter(output_file) as writer:
    preprocessed.to_excel(writer, sheet_name='preprocessed')
    normalized.to_excel(writer, sheet_name='normalized')
    output.to_excel(writer, sheet_name='output')