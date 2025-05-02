# AI Multitool
A simple web frontend to interact with OpenAI's text chat, text-to-image services and StabilityAI's text-to-image service.

## Setup

### Windows
1. Add your OpenAI API and StabilityAI key to `run-user.ps1`
2. Install `python`, `pipenv` and `npm`
3. Install the typescript and sass compiler: `npm install -g typescript sass`
4. run `npm install`
5. run `pipenv sync`

## Running it

### Windows
1. Run the script:
    ```
    pipenv shell
    .\run-user.ps1
    ```

## Licenses

The main code is licensed under the MIT license. See LICENSE for more info.

showdown.min.js under MIT License from [showdownjs/showdown](https://github.com/showdownjs/showdown)

highlight.min.js under BSD 3-Clause License from [highlightjs/highlight.js](https://github.com/highlightjs/highlight.js)

Roboto-Light.ttf licensed under the SIL Open Font License, Version 1.1 . This license is available with a FAQ at: https://openfontlicense.org

The loading spinner 'chunk' is from loading.io under the Loading.io BY License:
Assets relesed under Loading.io BY License ( LD-BY / BY / BY License ) are free to use if you attribute to loading.io properly. To attribute, just add a link ( for using in websites ) or credit text ( for using in slide or video ) to loading.io.