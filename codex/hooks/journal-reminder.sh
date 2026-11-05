#!/bin/sh
# UserPromptSubmit hook: supply a reminder, never write to the vault itself.
cat >/dev/null
printf '%s\n' 'DuckBrain journal reminder: capture meaningful new decisions, root causes, or discoveries with the journal workflow when appropriate. If there is nothing new, do not write an entry.'
