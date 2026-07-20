# FOKG_fact_checking_engine
This project builds a GERBIL-compatible fact-checking result file for the SWC/AKSW RDF statement task.  The engine reads RDF statements from N-Triples/Turtle-like files, learns simple statistical patterns from the labeled training facts, and predicts a truth value between `0.0` and `1.0` for each test fact.
