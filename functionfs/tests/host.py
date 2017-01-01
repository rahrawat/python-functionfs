# This file is part of python-functionfs
# Copyright (C) 2016  Vincent Pelletier <plr.vincent@gmail.com>
#
# python-functionfs is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# python-functionfs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with python-functionfs.  If not, see <http://www.gnu.org/licenses/>.
from time import time
import usb1
from . import common

def main():
    with usb1.USBContext() as context:
        handle = context.openByVendorIDAndProductID(
            0x1d6b,
            0x0104,
            skip_on_error=True,
        )
        if handle is None:
            print 'Device not found'
        device = handle.getDevice()
        assert len(device) == 1
        configuration = device[0]
        assert len(configuration) == 1
        interface = configuration[0]
        assert len(interface) == 1
        alt_setting = interface[0]
        lang_id, = handle.getSupportedLanguageList()
        interface_name = handle.getStringDescriptor(alt_setting.getDescriptor(), lang_id)
        assert interface_name == common.INTERFACE_NAME, repr(interface_name)

        try:
            handle.controlRead(
                usb1.TYPE_VENDOR | usb1.RECIPIENT_INTERFACE,
                common.REQUEST_STALL,
                0,
                0,
                1,
            )
        except usb1.USBErrorPipe:
            pass
        else:
            raise ValueError('Did not stall')

        try:
            handle.controlWrite(
                usb1.TYPE_VENDOR | usb1.RECIPIENT_INTERFACE,
                common.REQUEST_STALL,
                0,
                0,
                'a',
            )
        except usb1.USBErrorPipe:
            pass
        else:
            raise ValueError('Did not stall')

        echo_value = None
        for length in xrange(1, 65):
            echo_next_value = handle.controlRead(
                usb1.TYPE_VENDOR | usb1.RECIPIENT_INTERFACE,
                common.REQUEST_ECHO,
                0,
                0,
                length,
            )
            if echo_next_value == echo_value:
                break
            print repr(echo_next_value)
            echo_value = echo_next_value
        handle.controlWrite(
            usb1.TYPE_VENDOR | usb1.RECIPIENT_INTERFACE,
            common.REQUEST_ECHO,
            0,
            0,
            'foo bar baz',
        )
        print repr(handle.controlRead(
            usb1.TYPE_VENDOR | usb1.RECIPIENT_INTERFACE,
            common.REQUEST_ECHO,
            0,
            0,
            64,
        ))

        # XXX: untested (DWC3 bug on 4.9/4.10 ?)
        size = [0]
        def onTransfer(transfer):
            result = time() < deadline
            if result:
                size[0] += transfer.getActualLength()
            return result

        usb_file_data_reader = usb1.USBTransferHelper()
        usb_file_data_reader.setEventCallback(
            usb1.TRANSFER_COMPLETED,
            onTransfer,
        )
        transfer_list = []
        for _ in xrange(8):
            transfer = handle.getTransfer()
            transfer.setBulk(
                1 | usb1.ENDPOINT_IN,
                0x8000,
                callback=usb_file_data_reader,
                timeout=5000,
            )
            transfer.submit()
            transfer_list.append(transfer)

        deadline = time() + 5
        while any(x.isSubmitted() for x in transfer_list):
            context.handleEvents()
        print 'IN bandwidth: %.2f' % (size[0], )

if __name__ == '__main__':
    main()