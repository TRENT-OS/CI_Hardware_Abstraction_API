#
# Copyright (C) 2024, HENSOLDT Cyber GmbH
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# For commercial licensing, contact: info.cyber@hensoldt.net
#

source venv/bin/activate

SSH_TARGET="uart-proxy@10.178.169.36"


python3 -m build --wheel

rsync -avh --progress dist/uart_proxy-0.0.4-py3-none-any.whl ${SSH_TARGET}:/tmp/

TERM=xterm


ssh ${SSH_TARGET} << EOF
	cd uart_proxy
	source venv/bin/activate
	pip uninstall uart_proxy -y
	pip install /tmp/uart_proxy-0.0.4-py3-none-any.whl --no-input
	restart-uart-proxy
EOF
