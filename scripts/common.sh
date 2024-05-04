#!/bin/bash
assert_commands_exist () {
    for cmd in ${REQUIRED_COMMANDS[@]}; do
        command -v $cmd &>/dev/null
        if [ $? == 1 ]; then
            echo "Unable to find command: $cmd" 1>&2
            exit 1
        fi
    done
}

validate_env_vars () {
    for var in ${REQUIRED_ENV_VARS[@]}; do
        if [[ -z `echo ${!var}` ]]; then
            echo "Unable to environment variable: $var" 1>&2
            exit 1
        fi
    done
}

test_http_connection () {
    vault_address=$1
    expceted_response_code=$2
    
    status_code=$(curl -s -o /dev/null -w "%{http_code}" $vault_address)
    cmd_code=$?

    if [ $cmd_code != 0 ]; then
        echo "curl command failed. Code: $cmd_code" 1>&2
        exit 1
    fi

    if [ $status_code != $expceted_response_code ]; then
        echo "Unexpected response from vault server." 1>&2
        echo "Wanted $expceted_response_code but got $status_code" 1>&2
        echo "Server: $vault_address" 1>&2
        exit 1
    fi
}

regex_extract () {
    local haystack=$1 regex_pattern=$2 match_group=$3
    echo $haystack | sed "s/$regex_pattern/\\$match_group/"
}