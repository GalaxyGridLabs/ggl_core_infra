#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
. "$parent_path/common.sh"

REQUIRED_COMMANDS=("vault" "curl" "sed" "echo")
REQUIRED_ENV_VARS=("VAULT_ADDR")

parse_root_token () {
    init_output=$@
    root_token=$(regex_extract "$init_output" '.*Initial Root Token: \(.*\) Success!.*' 1 )
    echo "$root_token"
}

vault_init () {
    res=$(vault operator init 2>&1)
    res_code=$?
    if [ $res_code == 2 ]; then
        if [[ $res == *"Your client does not have permission to get URL"* ]]; then 
            echo "Vault may already have been initalized." 1>&2
            echo "Recieved: $res" 1>&2
            exit 2
        else
            exit 1
        fi
    else
        root_token=$(parse_root_token $res)
        echo $root_token
        exit 0
    fi
}

pre_flight () {
    assert_commands_exist
    validate_env_vars
    test_http_connection $VAULT_ADDR 307
}

main () {
    pre_flight
    init_output=$(vault_init)
    res_code=$?
    if [ $res_code == 0 ]; then
        jq -n --arg init_output "$init_output" '{"success":$init_output}'
        exit 0
    elif [ $res_code == 2 ]; then
        jq -n '{"error":"Already initalized"}'
        exit 2
    else
        jq -n '{"error":"Vault init failed"}'
        exit 1
    fi
}
main