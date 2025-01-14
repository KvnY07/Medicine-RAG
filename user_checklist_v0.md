You need to generate a list of drug production requirements based on the information provided. This list is used by drug manufacturers to confirm whether their production procedures meet the requirements of relevant laws and regulations. Please output a Markdown formatted checklist containing check items regarding **Documentation** based on the inputs.

### Input content:
1. **Pharmaceutical Manufacturing Requirements Provisions** (Regulatory or internal requirements for pharmaceutical manufacturing, e.g., GMP specifications, quality management regulations, etc.). : {gmp_data}
2. **Nature, type, and characteristics of drug** (Nature (e.g., liquid, tablet), type (e.g., antibiotic, painkiller), and characteristics (e.g., volatile, need to be stored at low temperature, etc.). : {chara}

### Sample output.
**1. Are there water systems used in the manufacture that are designed,
constructed and maintained?**
**2. Are there production areas for the production of medicinal products?**
**2.1 Are production areas equipped with facilities and instruments used in the production of medicinal products? (except for contract manufacture)**


### Output requirements:
Generate a checklist of drug manufacturing requirements in Markdown format with detailed check items only regarding **Documentation** based on the inputs.
    -The number of questions should be 2.
    -After each question, add a fragment of the original content of the text from which you designed the question. It should not be too long, no more than 100 words.
