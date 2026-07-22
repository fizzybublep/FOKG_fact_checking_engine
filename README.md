# FOKG_fact_checking_engine

This project builds a GERBIL-compatible fact-checking result file for the SW 2022 fact-checking task.

The system reads RDF statement data, learns simple statistical patterns from labeled training facts, predicts truth values for test facts, and writes a `result.ttl` file for GERBIL evaluation.

## Student Information
Name : Bobby Patel
Matriculation Number : 4053863

## Project Goal

Given a fact represented as an RDF statement, predict a veracity value between:

```text
0.0 = false
1.0 = true
```

Example fact:

```text
Venus_Williams birthPlace Lynwood,_California
```

The output must contain one score per fact.

## Project Files

```text
FOKG_fact_checking_engine/
  Data/
    KG-2022-test.nt.txt
    KG-2022-train.nt.txt
  outputs/
    result.ttl
  src/
    FACT_CHECKING_ENGINE.py
  .gitignore
  README.md
  requirements.txt
```

## Setup

This project does not require any external Python packages, so it can be run directly if Python 3.10 or newer is installed.

Optional virtual environment setup:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Running The Project

After cloning the repository, the required files are already included in the project structure:

```text
FOKG_fact_checking_engine/
  src/
    FACT_CHECKING_ENGINE.py
  data/
    KG-2022-train.nt.txt
    KG-2022-test.nt.txt
```

Then run:

```powershell
python .\src\FACT_CHECKING_ENGINE.py --train ".\data\KG-2022-train.nt.txt" --test ".\data\KG-2022-test.nt.txt" --output ".\outputs\result.ttl"
```

## Output File

The script creates:

```text
outputs/result.ttl
```
Note : Since the repository already has the result.ttl file, the script will output the new generated "result.ttl" in the same directory again and replace the old one.

Each line has this format:

```ttl
<FACT_URI> <http://swc2017.aksw.org/hasTruthValue> "0.731245"^^<http://www.w3.org/2001/XMLSchema#double> .
```

This is the file to upload to GERBIL.

## GERBIL Evaluation

Use GERBIL for the official evaluation:

```text
http://gerbil-kbc.aksw.org/gerbil/config
```

Choose:

```text
Task : Fact Checking
Submission : Add name, email-address and select file "result.ttl"
Reference dataset: SW 2022 Test
Agree to the Disclaimer
Run the Experiment
```

## GERBIL SCORE GENERATED
Final Score : 0.679
https://gerbil-kbc.aksw.org/gerbil/experiment?id=202607200001

## Method Summary

The model is a simple statistical baseline.

It learns from the labeled training facts by counting patterns such as:

```text
predicate truth rate
subject truth rate
object truth rate
subject-predicate truth rate
predicate-object truth rate
exact triple evidence
functional predicate behavior
```

Then it combines these signals into a final score between `0.0` and `1.0` for every test fact.
