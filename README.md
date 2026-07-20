# FOKG_fact_checking_engine

This project builds a GERBIL-compatible fact-checking result file for the SW 2022 fact-checking task.

The system reads RDF statement data, learns simple statistical patterns from labeled training facts, predicts truth values for test facts, and writes a `result.ttl` file for GERBIL evaluation.

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

'''text
FOKG_fact_checking_engine/
  Data/
    KG-2022-test.nt (1).txt
    KG-2022-train.nt (1).txt
  outputs/
    result.ttl
  src/
    fact_check.py
  .gitignore
  README.md
  requirements.txt
'''

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Even though there are no external packages, using a virtual environment is good practice for reproducibility.

## Running The Project

Place the provided dataset files in a `data/` folder:

```text
data/KG-2022-train.nt.txt
data/KG-2022-test.nt.txt
```

Then run:

```powershell
python .\src\fact_check.py --train ".\data\KG-2022-train.nt.txt" --test ".\data\KG-2022-test.nt.txt" --output ".\outputs\result.ttl"
```

## Optional Benchmark

To run the internal 5-fold benchmark on the training data:

```powershell
python .\src\fact_check.py --train ".\data\KG-2022-train.nt.txt" --test ".\data\KG-2022-test.nt.txt" --output ".\outputs\result.ttl" --benchmark
```

This prints an estimated AUC score using the labeled training data. The official score is still the GERBIL score.

## Output File

The script creates:

```text
outputs/result.ttl
```

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
Experiment type: Fact Checking
Reference dataset: SW 2022 Test
Result file: outputs/result.ttl
```
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
