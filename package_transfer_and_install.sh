source venv/bin/activate

python3 -m build --wheel

rsync -avh --progress dist/uart_proxy-0.0.3-py3-none-any.whl dietpi@192.168.88.4:/tmp/

TERM=xterm


ssh dietpi@192.168.88.4 << EOF
	cd uart_proxy
	source venv/bin/activate
	pip uninstall uart_proxy -y
	pip install /tmp/uart_proxy-0.0.3-py3-none-any.whl --no-input
	#/sbin/reboot
EOF
