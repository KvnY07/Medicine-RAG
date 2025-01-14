You are asked to generate information on the nature, type and characteristics of the drug based on the input drug profile information and extract a series of keywords. These keywords will be used to retrieve the provisions of the GMP specification related to Production Area from an external knowledge base for subsequent generation of the Drug Manufacturing Checklist.

### Input content:
1. **medication profile information**: {med_info}

### Production checklist example:

**1. Are there production areas for the production of medicinal products?**
**1.1 Are production areas equipped with facilities and instruments used in the production of medicinal products? (except for contract manufacture)**
**1.2 Are production areas for sterile products (injections, ophthalmic solutions, ophthalmic ointments), biological preparations, penicillins or sex hormones separated from other production areas by using different HVAC systems, entrances and exits, drains, etc? (If closed systems to prevent cross-contamination are used, the separation may not be required.)
**1.3 Are the operations performed in the segregated or defined area as per the dosage forms of medicinal products (injections, ophthalmic solutions, oral liquids, solutions for external use, ointments, oral solids, etc.)? (If closed systems to prevent cross-contamination are used, the separation may not be required.)**
**1.4 Are there water systems used in the manufacture that are designed, constructed and maintained?**
**1.5 Are there the facilities for preventing rats, vermin or dust from taking place?**
**1.6 Are there changing rooms, hand washing facilities, and disinfection facilities if necessary (e.g. production areas for sterile products, oral liquids, ointments)?**
**1.7 Is manufacturing of medicinal products performed in specifically defined or separated work areas depending on the kinds of products, the dosage forms or the production methods and production facilities? (It may be optional for weighing room of raw material, packaging area of product and washing room of product container. Certain work areas could be optional if it is approved by the commissioner of the Korea Food and Drug Administration).**
**1.8 Are work areas equipped with the following?**
**1.8.1) a worktable**
**1.8.2) a dust collection system if dust is generated in the work area**
**1.8.3) a humidity control system if any hygroscopic material is used in operations**
**1.8.4) a drying facility with automatic temperature controller, if necessary**

### Output requirements:
**Output the following in json format**:
1. **name** : str. Name of the drug product
2. **type** : str. Type of drug(e.g. sterile, herbal, generic, etc.)
3. **nature** : str. Nature of drug(e.g. solid, liquid, tablet, capsule, etc.)
4. **usage** : str. Types of medicines(e.g.: antibiotics, painkillers, hormonal drugs, etc.)
5. **characteristics** : list. Characteristics of pharmaceuticals(e.g. volatile, need to be stored at low temperatures, sensitive to light, etc.)
6. **keywords** : list. Extracted keywords used to search for Production Area related regulations in GMPs.

### Requirements for keywords:
You need to list ten keywords based on all the following aspects to retrieve the provisions of the GMP specification only related to **Production Area**. If there is a specific category of aspect, please first determine the category it belongs to and then list the related keywords:
**1. Type of medicine:**
- Herbal medicines (herbal products)
  (containing herbal ingredients or extracts)
  - Source of raw materials (cultivation, collection, pesticide use, etc.) (herbal materials)
  - Herbal medicines handling and quality control measures

- Aseptic medicines (sterile products)
  (e.g., injections, eye drops, etc.)
  - Aseptic handling and validation requirements
  - Storage requirements (temperature and humidity control, isolated storage, etc.)

- General drugs
  (e.g. tablets, capsules and other non-sterile preparations)
  - General production process requirements (e.g. mixing, pressing, packaging, etc.)

**2. Pharmaceutical dosage forms:**

- Solid dosage forms
  (tablets, granules, powders, etc.)
  - Production processes for solid drugs (e.g. pressing, mixing, coating, etc.)
  - Quality control standards (fineness, microbial content, content, etc.)

- Liquid dosage forms
  (oral liquids, injections, etc.)
  - Aseptic production requirements for liquid drugs (e.g., filtration, sterilization, etc.)
  - Quality control of liquids (e.g. viscosity, pH, solubility, etc.)

- Topical preparations
  (creams, gels, etc.)
  - Quality control of topical formulations (stability, microbiological testing, etc.)

**3. Production process:**

- Whether special processes are required
  - (e.g., extraction, fermentation, concentration, drying, etc.)
  - Whether physical or chemical treatment is involved (e.g. solvent extraction, distillation, etc.)
- Aseptic operation requirements
  - Whether aseptic operation is involved (e.g. injections, eye drops, etc.)
- Other special processes
  - Does it involve physical treatment processes such as pressing, mixing, coating, etc.

**4. Storage requirements:**

- Temperature and humidity control
  - Whether specific temperature and humidity control is required, especially for storage of herbal drugs, sterile drugs
- Storage area isolation requirements
  - Whether separate storage areas are required to prevent contamination or cross-contamination
- Protective measures
  - Whether special protective measures are needed to prevent rodents, insects, and direct sunlight, etc.

**5. Quality management requirements:**

- Validation requirements
  - Whether validation activities are required (e.g., extraction process validation for herbal drugs, sterility validation, etc.)
  - Whether special quality control validation is involved (e.g. stability testing, microbiological testing, etc.)
- Lot and control number management
  - Whether strict management by lot number and control number is required
- Cleaning and hygiene management
  - Whether special cleaning standards are required, especially in the production of sterile and herbal drugs

**6. Ingredients:**

- Ingredients of medicines
  - Whether it contains herbal ingredients, extracts, synthetic ingredients, etc.
  - Whether natural plant or synthetic chemical ingredients are used
- Detailed information about the herbal ingredient
  - Detailed information on how the herb is grown, how it is collected, pesticide use, etc.

**7.Regulatory requirements:**

- Compliance with local drug regulations
  - Compliance with local pharmaceutical manufacturing quality management regulations (e.g., Chinese GMP, FDA, and other international standards)
- Compliance with GMP (Good Manufacturing Practice) requirements
  - Special requirements especially in the production of herbal drugs, e.g. source of raw materials, production environment, etc.

**8. Manufacturing and quality control standards:**

- Special requirements for herbal medicines
  - Availability of special quality standards, production processes and storage requirements for herbal medicines
- Lot traceability and record management
  - Is lot traceability required for all medicines to ensure traceability and quality assurance?
- Validation, stability and microbiological testing
  - Are there additional stability validation and microbiological control requirements for herbal and sterile drugs?
