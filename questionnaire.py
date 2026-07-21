from __future__ import annotations

from collections import OrderedDict

DONT_KNOW = "Don’t know"

GENDER_OPTIONS = ["Male", "Female", "Prefer not to say", "Other"]
EDUCATION_OPTIONS = ["Undergraduate", "Postgraduate", "Doctoral", "Other"]
BACKGROUND_OPTIONS = ["Healthcare/Life Sciences", "Non-Healthcare"]
YES_NO = ["Yes", "No"]
YES_NO_DK = ["Yes", "No", DONT_KNOW]
TRUE_FALSE_DK = ["True", "False", DONT_KNOW]

B2_OPTIONS = ["Pancreas", "Liver", "Gallbladder", "Stomach", DONT_KNOW]
B3_OPTIONS = [
    "Abnormal and uncontrolled growth of cells in the pancreas",
    "Infection of the pancreas",
    "Temporary inflammation of the pancreas",
    "Formation of stones in the pancreas",
    DONT_KNOW,
]
C2_OPTIONS = [
    "Seek medical consultation promptly",
    "Wait for the symptoms to improve on their own",
    "Self-medicate without seeking professional advice",
    "Ignore the symptoms",
]

B_QUESTIONS = OrderedDict(
    [
        ("B1", "Before today, had you heard of pancreatic cancer?"),
        ("B2", "Which organ is primarily affected in pancreatic cancer?"),
        ("B3", "Which of the following best describes pancreatic cancer?"),
        ("B4", "Pancreatic cancer is often diagnosed at an advanced stage."),
        ("B5", "Earlier diagnosis of pancreatic cancer may improve treatment options."),
    ]
)

SYMPTOM_QUESTIONS = OrderedDict(
    [
        ("C1_1", "Jaundice or yellowing of the skin or eyes"),
        ("C1_2", "Persistent upper abdominal pain"),
        ("C1_3", "Persistent back pain"),
        ("C1_4", "Unexplained weight loss"),
        ("C1_5", "Loss of appetite"),
        ("C1_6", "New-onset diabetes or an unexplained change in blood glucose control"),
        ("C1_7", "Dark urine"),
        ("C1_8", "Pale or light-coloured stools"),
        ("C1_9", "Persistent sore throat"),
        ("C1_10", "Hair loss"),
        ("C1_11", "Knee pain following physical activity"),
        ("C1_12", "A minor skin rash caused by an insect bite"),
    ]
)

D_QUESTIONS = OrderedDict(
    [
        ("D1", "Having a close family member with pancreatic cancer can increase a person’s risk of developing pancreatic cancer."),
        ("D2", "Some inherited genetic variants, including harmful variants in genes such as BRCA1 and BRCA2, can increase pancreatic cancer risk."),
        ("D3", "Individuals with a strong family history of pancreatic cancer may benefit from genetic counselling and professional risk assessment."),
        ("D4", "Selected individuals at high inherited or familial risk may be advised by specialists to undergo pancreatic surveillance."),
    ]
)

E_QUESTIONS = OrderedDict(
    [
        ("E1", "I believe I understand the basic facts about pancreatic cancer."),
        ("E2", "I believe pancreatic cancer is a serious disease."),
        ("E3", "I believe pancreatic cancer can occur even in people who do not have a known family history of the disease."),
        ("E4", "I believe people with a strong family history of pancreatic cancer may have a greater risk of developing the disease."),
        ("E5", "I believe recognizing possible warning signs and seeking timely medical advice is important."),
    ]
)

F_QUESTIONS = OrderedDict(
    [
        ("F1", "If I had a strong family history of pancreatic cancer, I would consider genetic counselling and genetic testing if recommended by a qualified healthcare professional."),
        ("F2", "If I were identified as being at high risk, I would undergo pancreatic surveillance if recommended by an appropriate specialist."),
        ("F3", "I would seek medical consultation if I developed persistent or concerning symptoms that could be associated with pancreatic cancer."),
        ("F4", "I would encourage family members who may be at increased risk to seek professional advice about genetic counselling or surveillance."),
        ("F5", "I would be willing to participate in future pancreatic cancer awareness or risk-based screening programmes for which I was eligible."),
    ]
)

G_SOURCES = OrderedDict(
    [
        ("G1", "Healthcare professional"),
        ("G2", "Hospital or cancer awareness programme"),
        ("G3", "Scientific articles or academic publications"),
        ("G4", "Government or recognized health-organization websites"),
        ("G5", "Social media"),
        ("G6", "Family or friends"),
        ("G7", "Television, newspapers, magazines, or other mass media"),
        ("G8", "I have never previously received information about pancreatic cancer"),
        ("G9", "Other source"),
    ]
)

OBJECTIVE_KEY = {
    "B2": "Pancreas",
    "B3": "Abnormal and uncontrolled growth of cells in the pancreas",
    "B4": "True",
    "B5": "True",
    "C1_1": "Yes",
    "C1_2": "Yes",
    "C1_3": "Yes",
    "C1_4": "Yes",
    "C1_5": "Yes",
    "C1_6": "Yes",
    "C1_7": "Yes",
    "C1_8": "Yes",
    "C1_9": "No",
    "C1_10": "No",
    "C1_11": "No",
    "C1_12": "No",
    "D1": "True",
    "D2": "True",
    "D3": "True",
    "D4": "True",
}

B_SCORED_ITEMS = ["B2", "B3", "B4", "B5"]
C1_ITEMS = [f"C1_{i}" for i in range(1, 13)]
D_ITEMS = ["D1", "D2", "D3", "D4"]
CORE_ITEMS = B_SCORED_ITEMS + C1_ITEMS + D_ITEMS
E_ITEMS = [f"E{i}" for i in range(1, 6)]
F_ITEMS = [f"F{i}" for i in range(1, 6)]
G_ITEMS = [f"G{i}" for i in range(1, 10)]
REQUIRED_RESPONSE_ITEMS = ["B1"] + CORE_ITEMS + ["C2"] + E_ITEMS + F_ITEMS

ITEM_LABELS = {
    **B_QUESTIONS,
    **SYMPTOM_QUESTIONS,
    "C2": "Help-seeking intention",
    **D_QUESTIONS,
    **E_QUESTIONS,
    **F_QUESTIONS,
    **G_SOURCES,
}
