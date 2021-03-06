from enum import Enum
import uuid
from nio import Block
from nio.block.mixins import EnrichSignals 
from nio.properties import BoolProperty, ObjectProperty, Property, \
    PropertyHolder, SelectProperty, StringProperty, VersionProperty


class UUIDnamespace(Enum):

    DNS = 'DNS'
    URL = 'URL'
    OID = 'OID'
    X500 = 'X500'
    Custom = 'custom'

class UUIDversions(Enum):

    v1 = 1
    v3 = 3
    v4 = 4
    v5 = 5

class UUIDname(PropertyHolder):

    custom_name_space = Property(
        title='Custom Namespace',
        allow_none=True,
        order=2)
    name_space = SelectProperty(
        UUIDnamespace,
        title='Namespace',
        default=UUIDnamespace.DNS,
        order=1)
    name_string = StringProperty(
        title='Name',
        allow_none=True,
        order=0)

class UUID(EnrichSignals, Block):

    binary = BoolProperty(
        title='Binary Output',
        default=False,
        advanced=True)
    output = StringProperty(
        title='Output Attribute',
        default='uuid',
        advanced=True)
    uuid_name = ObjectProperty(
        UUIDname,
        title='Name Options (versions 3 and 5 only)',
        order=1,
        advanced = True)
    uuid_version = SelectProperty(
        UUIDversions,
        title='UUID Version',
        default=UUIDversions.v4,
        order=0,
        advanced=True)
    version = VersionProperty('0.1.0')

    def process_signal(self, signal, input_id=None):
        new_uuid = self._get_new_uuid(signal)
        if new_uuid is None:
            # failed, an error has been logged
            return
        if not self.binary():
            new_uuid = str(new_uuid)
        else:
            new_uuid = new_uuid.bytes
        new_signal = {self.output(signal): new_uuid}
        return self.get_output_signal(new_signal, signal)

    def _get_new_uuid(self, signal):
        version = self.uuid_version(signal).value
        version_string = 'uuid{}'.format(version)
        if version in [1, 4]:
            return getattr(uuid, version_string)()
        name = self.uuid_name().name_string(signal)
        namespace = self.uuid_name().name_space(signal).value
        if namespace == 'custom':
            custom_name_space = self.uuid_name().custom_name_space(signal)
            if custom_name_space is None or not str(custom_name_space).strip():
                # an emtpy string or None has been given
                msg = '\"Custom Namespace\" parameter must be provided.'
                self.logger.error(msg)
                return
            if not isinstance(custom_name_space, uuid.UUID):
                namespace_uuid = self._load_uuid(custom_name_space, version)
                if not namespace_uuid:
                    # failed, an error has been logged
                    return
            else:
                namespace_uuid = custom_name_space
        else:
            namespace_uuid = getattr(uuid, 'NAMESPACE_{}'.format(namespace))
        try:
            new_uuid = getattr(uuid, version_string)(namespace_uuid, name)
        except TypeError as e:
            if name is None:
                msg = '\"Name\" parameter is required for UUID version {}'
                self.logger.error(msg.format(version))
                return
            raise e
        return new_uuid

    def _load_uuid(self, custom_name_space, version):
        if isinstance(custom_name_space, str):
            new_uuid = uuid.UUID(hex=custom_name_space, version=version)
        elif isinstance(custom_name_space, bytes):
            new_uuid = uuid.UUID(bytes=custom_name_space, version=version)
        else:
            custom_name_space_type = type(custom_name_space).__name__
            msg = 'Unexpected type for Custom Namespace: {}'
            self.logger.error(msg.format(custom_name_space_type))
            return
        return new_uuid
