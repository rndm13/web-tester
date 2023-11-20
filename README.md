Uses [fuzzdb](https://github.com/fuzzdb-project/fuzzdb)

# Features
- [x] Writing tests
    - [x] Specifying http type
    - [x] Specifying body type
        - [x] Different inputs depend on body type
        - [x] Auto formatting json
        - [x] Changes according to formats
    - [x] Specify cookies
    - [x] Specify headers
    - [x] Specify everything mentioned above for expected response
    - [x] Select max timeout time for request
    - [x] Select tests and options for those tests you want to run
- [x] Running tests
    - [x] Basic tests
        - [x] Run in parallel
    - [x] Dynamic tests
        - [x] Run sequentially but keeping track of cookies
    - [x] Can be cancelled
- [x] Analyzing test results
    - [x] Checks for errors in response using selected wordlist
