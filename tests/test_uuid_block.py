import uuid
from unittest.mock import ANY, Mock, patch
from nio import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..uuid_block import UUID


class MockedUUIDclass(uuid.UUID):

    mocked = Mock(spec=uuid.UUID)

    def __new__(cls, *args, **kwargs):
        return cls.mocked(*args, **kwargs)

class TestUUID(NIOBlockTestCase):

    @patch('uuid.uuid4')
    def test_new_uuid(self, mock_uuid4):
        """By default a new UUID4 is added to every signal processed."""
        mock_uuid_obj = Mock()
        mock_uuid_obj.__str__ = Mock(return_value='foobarbaz')
        mock_uuid4.return_value = mock_uuid_obj
        blk = UUID()
        config = {
            'output': '{{ $output }}',
        }
        self.configure_block(blk, config)
        blk.start()
        blk.process_signals([Signal({'output': 'foo'})])
        blk.stop()
        self.assert_num_signals_notified(1)
        self.assert_last_signal_notified(Signal({
            'foo': 'foobarbaz',
        }))
        mock_uuid4.assert_called_once_with()

    @patch('uuid.uuid5')
    @patch('uuid.uuid4')
    @patch('uuid.uuid3')
    @patch('uuid.uuid1')
    def test_uuid_versions(
            self, mock_uuid1, mock_uuid3, mock_uuid4, mock_uuid5):
        """All supported versions and their options are implemented."""
        mock_uuid_obj = Mock()
        mock_uuid_obj.__str__ = Mock(return_value='foobarbaz')
        mock_uuid1.return_value = mock_uuid_obj
        mock_uuid3.return_value = mock_uuid_obj
        mock_uuid4.return_value = mock_uuid_obj
        mock_uuid5.return_value = mock_uuid_obj
        blk = UUID()
        config = {
            'uuid_name': {
                'name_string': 'niolabs.com',
            },
            'uuid_version': '{{ $uuid_version }}'
        }
        self.configure_block(blk, config)
        blk.start()
        blk.process_signals([
            Signal({'uuid_version': 1}),
            Signal({'uuid_version': 3}),
            Signal({'uuid_version': 4}),
            Signal({'uuid_version': 5}),
        ])
        blk.stop()
        self.assert_num_signals_notified(4)
        self.assertEqual(mock_uuid1.call_args[0], ())
        self.assertEqual(
            mock_uuid3.call_args[0],
            (uuid.NAMESPACE_DNS, 'niolabs.com'))
        self.assertEqual(mock_uuid4.call_args[0], ())
        self.assertEqual(
            mock_uuid5.call_args[0],
            (uuid.NAMESPACE_DNS, 'niolabs.com'))

    @patch('uuid.uuid5')
    def test_namespace_options(self, mock_uuid5):
        """Namespace options for versions 3 and 5 are supported."""
        mock_uuid_obj = Mock()
        mock_uuid_obj.__str__ = Mock(return_value='foobarbaz')
        mock_uuid5.return_value = mock_uuid_obj
        blk = UUID()
        config = {
            'uuid_name': {
                'name_string': 'niolabs.com',
                'name_space': '{{ $namespace }}',
            },
            'uuid_version': 5,
        }
        self.configure_block(blk, config)
        blk.start()
        blk.process_signals([
            Signal({'namespace': 'DNS'}),
            Signal({'namespace': 'URL'}),
            Signal({'namespace': 'OID'}),
            Signal({'namespace': 'X500'}),
        ])
        blk.stop()
        self.assertEqual(
            mock_uuid5.call_args_list[0][0],
            (uuid.NAMESPACE_DNS, 'niolabs.com'))
        self.assertEqual(
            mock_uuid5.call_args_list[1][0],
            (uuid.NAMESPACE_URL, 'niolabs.com'))
        self.assertEqual(
            mock_uuid5.call_args_list[2][0],
            (uuid.NAMESPACE_OID, 'niolabs.com'))
        self.assertEqual(
            mock_uuid5.call_args_list[3][0],
            (uuid.NAMESPACE_X500, 'niolabs.com'))

    @patch('uuid.uuid4')
    def test_signal_enrichment(self, mock_uuid4):
        """Signal Enrichment is implemented."""
        mock_uuid_obj = Mock()
        mock_uuid_obj.__str__ = Mock(return_value='foobarbaz')
        mock_uuid4.return_value = mock_uuid_obj
        config = {
            'enrich': {'exclude_existing': False},
        }
        blk = UUID()
        self.configure_block(blk, config)
        blk.start()
        blk.process_signals([Signal({'pi': 3.14})])
        blk.stop()
        self.assert_last_signal_notified(Signal({
            'pi': 3.14,
            'uuid': 'foobarbaz',
        }))

    @patch('uuid.uuid4')
    def test_binary_output(self, mock_uuid4):
        """Optinal binary output instead of canonical hex string."""
        mock_uuid_obj = Mock()
        mock_uuid_obj.bytes = b'foo'
        mock_uuid_obj.__str__ = Mock(side_effect=str)  # must return string
        mock_uuid4.return_value = mock_uuid_obj
        blk = UUID()
        config = {
            'binary': True,
        }
        self.configure_block(blk, config)
        blk.start()
        blk.process_signals([Signal()])
        blk.stop()
        self.assert_last_signal_notified(Signal({
            'uuid': b'foo',
        }))

    def test_missing_name_option(self):
        """When name is required and not given the exception is handled
        and a helpful message is logged.
        """
        blk = UUID()
        # empty strings are valid for a name so we only test a None type
        config = {
            'name_string': None,
            'uuid_version': '{{ $uuid_version }}',
        }
        self.configure_block(blk, config)
        blk.start()
        blk.process_signals([
            Signal({'uuid_version': 3}),
            Signal({'uuid_version': 5}),
        ])
        blk.stop()
        self.assert_num_signals_notified(0)

    @patch('uuid.uuid5')
    def test_custom_namespace(self, mock_uuid5):
        """A custom namespace can be used."""
        blk = UUID()
        config = {
            'uuid_name': {
                'name_space': 'custom',
                'name_string': 'niolabs.com',
                'custom_name_space': '{{ $custom_name_space }}',
            },
            'uuid_version': 5,
        }
        self.configure_block(blk, config)
        blk.start()
        with patch('uuid.UUID', new=MockedUUIDclass):
            blk.process_signals([
                Signal({'custom_name_space': 'uuidString'}),
                Signal({'custom_name_space': b'uuidBytes'}),
            ])
        blk.stop()
        # two new UUIDs were loaded from provided string and bytes
        self.assertEqual(MockedUUIDclass.mocked.call_count, 2)
        self.assertDictEqual(
            MockedUUIDclass.mocked.call_args_list[0][1],
            {'hex': 'uuidString', 'version': 5})
        self.assertDictEqual(
            MockedUUIDclass.mocked.call_args_list[1][1],
            {'bytes': b'uuidBytes', 'version': 5})
        # a new UUID5 was created for each signal processed
        self.assertEqual(mock_uuid5.call_count, 2)
        self.assertEqual(
            mock_uuid5.call_args_list[0][0],
            (MockedUUIDclass.mocked.return_value, 'niolabs.com'))
        self.assertEqual(
            mock_uuid5.call_args_list[1][0],
            (MockedUUIDclass.mocked.return_value, 'niolabs.com'))

    @patch('uuid.uuid5')
    def test_custom_namespace_as_uuid(self, mock_uuid5):
        """Handle UUID objects for custom namespace"""
        # this is much easier to test on its own without mocking uuid.UUID
        dummy_uuid = uuid.UUID('00112233-4455-6677-8899-AABBCCDDEEFF')
        blk = UUID()
        config = {
            'uuid_name': {
                'name_space': 'custom',
                'name_string': 'niolabs.com',
                'custom_name_space': dummy_uuid,
            },
            'uuid_version': 5,
        }
        self.configure_block(blk, config)
        blk.start()
        blk.process_signals([Signal()])
        blk.stop()
        self.assertEqual(mock_uuid5.call_count, 1)
        self.assertEqual(
            mock_uuid5.call_args_list[0][0],
            (dummy_uuid, 'niolabs.com'))

    @patch('uuid.uuid5')
    def test_custom_namespace_without_value(self, mock_uuid5):
        """When custom namespace is selected and not given the exception is
        handled and a helpful message is logged.
        """
        blk = UUID()
        config = {
            'uuid_name': {
                'name_space': 'custom',
                'name_string': 'niolabs.com',
                'custom_name_space': '{{ $custom_name_space }}',
            },
            'uuid_version': 5,
        }
        self.configure_block(blk, config)
        blk.start()
        # both of these values should raise...
        blk.process_signals([
            Signal({'custom_name_space': None}),
            Signal({'custom_name_space': ''}),
        ])
        blk.stop()
        # but the block should catch and ignore those invalid values
        mock_uuid5.assert_not_called()
