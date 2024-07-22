source venv/bin/activate

SSH_TARGET="uart-proxy@192.168.88.4"


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
