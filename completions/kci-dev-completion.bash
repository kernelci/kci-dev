_kci_dev_completion() {
    local IFS=$'\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD="$COMP_CWORD" _KCI_DEV_COMPLETE=bash_complete "$1")

    for completion in $response; do
        IFS=',' read -r type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=("$value")
        fi
    done

    return 0
}

_kci_dev_completion_setup() {
    complete -o nosort -F _kci_dev_completion kci-dev
}

_kci_dev_completion_setup;

