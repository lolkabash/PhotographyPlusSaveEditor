"""Writer for the UE4 GVAS property types used by Photography Plus saves."""
import struct


class GvasWriter:
    def __init__(self):
        self.data = bytearray()

    def write(self, b):
        self.data.extend(b)

    def write_u32(self, v):
        self.data.extend(struct.pack('<I', v))

    def write_u16(self, v):
        self.data.extend(struct.pack('<H', v))

    def write_i32(self, v):
        self.data.extend(struct.pack('<i', v))

    def write_i64(self, v):
        self.data.extend(struct.pack('<q', v))

    def write_u64(self, v):
        self.data.extend(struct.pack('<Q', v))

    def write_f32(self, v):
        self.data.extend(struct.pack('<f', v))

    def write_f64(self, v):
        self.data.extend(struct.pack('<d', v))

    def write_string(self, s):
        if s == "":
            self.write_i32(0)
            return
        encoded = s.encode('utf-8') + b'\x00'
        self.write_i32(len(encoded))
        self.write(encoded)

    def write_guid(self, hex_str):
        self.write(bytes.fromhex(hex_str))

    def write_header(self, header):
        self.write(b'GVAS')
        self.write_u32(header['save_game_version'])
        self.write_u32(header['package_version'])
        self.write_u16(header['engine_version_major'])
        self.write_u16(header['engine_version_minor'])
        self.write_u16(header['engine_version_patch'])
        self.write_u32(header['engine_version_changelist'])
        self.write_string(header['engine_version_branch'])
        self.write_u32(header.get('custom_version_format', 3))
        
        custom_versions = header.get('custom_versions', [])
        self.write_u32(len(custom_versions))
        for cv in custom_versions:
            self.write_guid(cv['guid'])
            self.write_u32(cv['version'])

    def write_property(self, name, prop):
        self.write_string(name)
        self.write_string(prop['type'])
        
        # Write size placeholder, then value, then fix size
        size_offset = len(self.data)
        self.write_u64(0)  # placeholder
        
        value_start = len(self.data)
        self.write_property_value(prop['type'], prop['value'], name)
        value_end = len(self.data)
        
        # Calculate actual size (excluding the terminator byte for most types)
        actual_size = self.calc_property_size(prop['type'], prop['value'], name)
        struct.pack_into('<Q', self.data, size_offset, actual_size)

    def calc_property_size(self, type_name, value, prop_name=""):
        """Calculate the size field for a property (bytes after terminator)."""
        if type_name == "IntProperty":
            return 4
        elif type_name == "UInt32Property":
            return 4
        elif type_name == "Int64Property":
            return 8
        elif type_name == "UInt64Property":
            return 8
        elif type_name == "FloatProperty":
            return 4
        elif type_name == "DoubleProperty":
            return 8
        elif type_name == "BoolProperty":
            return 0
        elif type_name == "StrProperty" or type_name == "NameProperty":
            if value == "":
                return 4  # just the length field (0)
            encoded = value.encode('utf-8') + b'\x00'
            return 4 + len(encoded)
        elif type_name == "EnumProperty":
            # Size is the enum value string size
            v = value['value']
            if v == "":
                return 4
            encoded = v.encode('utf-8') + b'\x00'
            return 4 + len(encoded)
        elif type_name == "StructProperty":
            # Need to calculate struct body size
            w = GvasWriter()
            w.write_struct_body(value)
            return len(w.data)
        elif type_name == "ArrayProperty":
            w = GvasWriter()
            w.write_array_body(value, prop_name)
            return len(w.data)
        elif type_name == "ObjectProperty":
            if value == "":
                return 4
            encoded = value.encode('utf-8') + b'\x00'
            return 4 + len(encoded)
        elif type_name == "MapProperty":
            w = GvasWriter()
            w.write_map_body(value)
            return len(w.data)
        elif type_name == "ByteProperty":
            if isinstance(value, int):
                return 1
            else:
                v = value['value']
                if v == "":
                    return 4
                encoded = v.encode('utf-8') + b'\x00'
                return 4 + len(encoded)
        elif type_name == "SoftObjectProperty":
            size = 0
            for s in [value['asset_path'], value['sub_path']]:
                if s == "":
                    size += 4
                else:
                    size += 4 + len(s.encode('utf-8')) + 1
            return size
        return 0

    def write_property_value(self, type_name, value, prop_name=""):
        if type_name == "IntProperty":
            self.write(b'\x00')  # terminator
            self.write_i32(value)
        elif type_name == "UInt32Property":
            self.write(b'\x00')
            self.write_u32(value)
        elif type_name == "Int64Property":
            self.write(b'\x00')
            self.write_i64(value)
        elif type_name == "UInt64Property":
            self.write(b'\x00')
            self.write_u64(value)
        elif type_name == "FloatProperty":
            self.write(b'\x00')
            self.write_f32(value)
        elif type_name == "DoubleProperty":
            self.write(b'\x00')
            self.write_f64(value)
        elif type_name == "BoolProperty":
            self.write(b'\x01' if value else b'\x00')
            self.write(b'\x00')  # terminator
        elif type_name == "StrProperty" or type_name == "NameProperty":
            self.write(b'\x00')
            self.write_string(value)
        elif type_name == "EnumProperty":
            self.write_string(value['enum_type'])
            self.write(b'\x00')
            self.write_string(value['value'])
        elif type_name == "StructProperty":
            struct_type = value.get('type', '')
            self.write_string(struct_type)
            self.write_guid('00000000000000000000000000000000')  # struct guid
            self.write(b'\x00')
            self.write_struct_body(value)
        elif type_name == "ArrayProperty":
            array_type = self.detect_array_type(value)
            self.write_string(array_type)
            self.write(b'\x00')
            self.write_array_body(value, prop_name)
        elif type_name == "ObjectProperty":
            self.write(b'\x00')
            self.write_string(value)
        elif type_name == "MapProperty":
            self.write_string(value['key_type'])
            self.write_string(value['value_type'])
            self.write(b'\x00')
            self.write_map_body(value)
        elif type_name == "ByteProperty":
            if isinstance(value, int):
                self.write_string("None")
                self.write(b'\x00')
                self.write(bytes([value]))
            else:
                self.write_string(value['enum'])
                self.write(b'\x00')
                self.write_string(value['value'])
        elif type_name == "SoftObjectProperty":
            self.write(b'\x00')
            self.write_string(value['asset_path'])
            self.write_string(value['sub_path'])

    def write_struct_body(self, value):
        struct_type = value.get('type', '')
        if struct_type == "Vector":
            self.write_f32(value['x'])
            self.write_f32(value['y'])
            self.write_f32(value['z'])
        elif struct_type == "Rotator":
            self.write_f32(value['pitch'])
            self.write_f32(value['yaw'])
            self.write_f32(value['roll'])
        elif struct_type == "Quat":
            self.write_f32(value['x'])
            self.write_f32(value['y'])
            self.write_f32(value['z'])
            self.write_f32(value['w'])
        elif struct_type == "LinearColor":
            self.write_f32(value['r'])
            self.write_f32(value['g'])
            self.write_f32(value['b'])
            self.write_f32(value['a'])
        elif struct_type == "Color":
            self.write(bytes([value['b'], value['g'], value['r'], value['a']]))
        elif struct_type == "Guid":
            self.write_guid(value['value'])
        elif struct_type == "DateTime" or struct_type == "Timespan":
            self.write_i64(value['ticks'])
        elif struct_type == "Vector2D":
            self.write_f32(value['x'])
            self.write_f32(value['y'])
        elif struct_type == "IntPoint":
            self.write_i32(value['x'])
            self.write_i32(value['y'])
        else:
            # Generic struct with properties
            props = value.get('properties', {})
            for pname, pval in props.items():
                self.write_property(pname, pval)
            self.write_string("None")

    def write_array_body(self, value, prop_name=""):
        if not value:
            self.write_u32(0)
            return
        
        # Detect array element type from first item
        if isinstance(value, list) and len(value) > 0:
            first = value[0]
            if isinstance(first, dict) and 'type' in first:
                # Struct array
                self.write_u32(len(value))
                struct_type = first.get('type', 'Generic')
                self.write_string(prop_name if prop_name else "")
                self.write_string("StructProperty")
                
                # Calculate total element size
                w = GvasWriter()
                for item in value:
                    w.write_struct_body(item)
                
                self.write_u64(len(w.data) // len(value) if value else 0)
                self.write_string(struct_type)
                self.write_guid('00000000000000000000000000000000')
                self.write(b'\x00')
                
                for item in value:
                    self.write_struct_body(item)
            elif isinstance(first, bool):
                self.write_u32(len(value))
                for item in value:
                    self.write(b'\x01' if item else b'\x00')
            elif isinstance(first, int):
                self.write_u32(len(value))
                for item in value:
                    self.write_i32(item)
            elif isinstance(first, float):
                self.write_u32(len(value))
                for item in value:
                    self.write_f32(item)
            elif isinstance(first, str):
                self.write_u32(len(value))
                for item in value:
                    self.write_string(item)
            else:
                self.write_u32(len(value))
        else:
            self.write_u32(0)

    def write_map_body(self, value):
        entries = value.get('entries', [])
        self.write_u32(0)  # removals
        self.write_u32(len(entries))
        for entry in entries:
            self.write_map_type(value['key_type'], entry['key'])
            self.write_map_type(value['value_type'], entry['value'])

    def write_map_type(self, type_name, value):
        if type_name == "IntProperty":
            self.write_i32(value)
        elif type_name in ("StrProperty", "NameProperty"):
            self.write_string(value)
        elif type_name == "FloatProperty":
            self.write_f32(value)
        elif type_name == "BoolProperty":
            self.write(b'\x01' if value else b'\x00')
        elif type_name == "EnumProperty":
            self.write_string(value)
        elif type_name == "StructProperty":
            for pname, pval in value.items():
                self.write_property(pname, pval)
            self.write_string("None")
        elif type_name == "ObjectProperty":
            self.write_string(value)

    def detect_array_type(self, value):
        if not value:
            return "IntProperty"
        first = value[0]
        if isinstance(first, dict) and 'type' in first:
            return "StructProperty"
        elif isinstance(first, bool):
            return "BoolProperty"
        elif isinstance(first, int):
            return "IntProperty"
        elif isinstance(first, float):
            return "FloatProperty"
        elif isinstance(first, str):
            return "StrProperty"
        return "IntProperty"
