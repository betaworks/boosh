#!/bin/bash

function benv () {
    case $1 in
        clear)
            unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID
            ;;
        run)
            local PROFILE=$2
            shift 2
            eval $(benv_creds --profile=$PROFILE) $@
            ;;
        *)
            if [[ -n "$2" ]]; then
                local PROFILE=$1
                shift 1
                eval $(benv_creds --profile=$PROFILE) $@
            else
                eval $(benv_creds --profile=$1)
                declare -x AWS_SECRET_ACCESS_KEY
                declare -x AWS_ACCESS_KEY_ID
            fi
            ;;
    esac
}
