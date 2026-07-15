"""Reader for the UE4 GVAS property types used by Photography Plus saves."""
import struct

class GvasReader:
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def read(self, n):
        result = self.data[self.offset:self.offset + n]
        self.offset += n
        return result

    def read_u32(self):
        return struct.unpack('<I', self.read(4))[0]

    def read_u16(self):
        return struct.unpack('<H', self.read(2))[0]

    def read_i32(self):
        return struct.unpack('<i', self.read(4))[0]

    def read_i64(self):
        return struct.unpack('<q', self.read(8))[0]

    def read_u64(self):
        return struct.unpack('<Q', self.read(8))[0]

    def read_f32(self):
        return struct.unpack('<f', self.read(4))[0]

    def read_f64(self):
        return struct.unpack('<d', self.read(8))[0]

    def read_bool(self):
        return self.read(1)[0] != 0

    def read_string(self):
        length = self.read_i32()
        if length == 0:
            return ""
        if length < 0:
            # UTF-16 encoded
            length = -length
            raw = self.read(length * 2)
            return raw[:-2].decode('utf-16-le')
        else:
            raw = self.read(length)
            return raw[:-1].decode('utf-8', errors='replace')

    def read_guid(self):
        raw = self.read(16)
        return raw.hex()

    def read_header(self):
        magic = self.read(4)
        if magic != b'GVAS':
            raise ValueError(f"Not a GVAS file (magic: {magic})")
        
        header = {}
        header['save_game_version'] = self.read_u32()
        header['package_version'] = self.read_u32()
        header['engine_version_major'] = self.read_u16()
        header['engine_version_minor'] = self.read_u16()
        header['engine_version_patch'] = self.read_u16()
        header['engine_version_changelist'] = self.read_u32()
        header['engine_version_branch'] = self.read_string()
        
        # Custom version format (should be 3)
        custom_version_format = self.read_u32()
        header['custom_version_format'] = custom_version_format
        
        custom_version_count = self.read_u32()
        header['custom_versions'] = []
        for _ in range(custom_version_count):
            guid = self.read_guid()
            version = self.read_u32()
            header['custom_versions'].append({'guid': guid, 'version': version})
        
        return header

    def read_property(self):
        name = self.read_string()
        if name == "None" or name == "":
            return None, None
        
        type_name = self.read_string()
        size = self.read_u64()
        
        value = self.read_property_value(type_name, size, name)
        return name, {'type': type_name, 'size': size, 'value': value}

    def read_property_value(self, type_name, size, prop_name=""):
        if type_name == "IntProperty":
            self.read(1)  # terminator
            return self.read_i32()
        elif type_name == "UInt32Property":
            self.read(1)
            return self.read_u32()
        elif type_name == "Int64Property":
            self.read(1)
            return self.read_i64()
        elif type_name == "UInt64Property":
            self.read(1)
            return self.read_u64()
        elif type_name == "FloatProperty":
            self.read(1)  # terminator
            return self.read_f32()
        elif type_name == "DoubleProperty":
            self.read(1)
            return self.read_f64()
        elif type_name == "BoolProperty":
            val = self.read(1)[0] != 0
            self.read(1)  # terminator
            return val
        elif type_name == "StrProperty" or type_name == "NameProperty" or type_name == "TextProperty":
            self.read(1)  # terminator
            if type_name == "TextProperty":
                # TextProperty has extra header bytes
                start = self.offset
                try:
                    # Try to read as text property
                    self.read(4)  # flags
                    hist_type = self.read(1)[0]
                    if hist_type == 255:  # None
                        has_culture = self.read_i32()
                        if has_culture == -1:
                            return ""
                        return self.read_string()
                    else:
                        self.offset = start
                        raw = self.read(size)
                        return raw.hex()
                except:
                    self.offset = start
                    raw = self.read(size)
                    return raw.hex()
            return self.read_string()
        elif type_name == "EnumProperty":
            enum_type = self.read_string()
            self.read(1)  # terminator
            enum_value = self.read_string()
            return {'enum_type': enum_type, 'value': enum_value}
        elif type_name == "StructProperty":
            struct_type = self.read_string()
            struct_guid = self.read_guid()
            self.read(1)  # terminator
            return self.read_struct(struct_type, size)
        elif type_name == "ArrayProperty":
            array_type = self.read_string()
            self.read(1)  # terminator
            return self.read_array(array_type, size, prop_name)
        elif type_name == "MapProperty":
            key_type = self.read_string()
            value_type = self.read_string()
            self.read(1)  # terminator
            return self.read_map(key_type, value_type, size)
        elif type_name == "ObjectProperty":
            self.read(1)  # terminator
            return self.read_string()
        elif type_name == "SoftObjectProperty":
            self.read(1)
            asset_path = self.read_string()
            sub_path = self.read_string()
            return {'asset_path': asset_path, 'sub_path': sub_path}
        elif type_name == "ByteProperty":
            enum_name = self.read_string()
            self.read(1)  # terminator
            if enum_name == "None":
                return self.read(1)[0]
            else:
                return {'enum': enum_name, 'value': self.read_string()}
        else:
            # Unknown type - read raw bytes
            self.read(1)  # terminator  
            raw = self.read(size)
            return f"<raw {size} bytes: {raw[:32].hex()}...>"

    def read_struct(self, struct_type, size):
        if struct_type == "Vector":
            x = self.read_f32()
            y = self.read_f32()
            z = self.read_f32()
            return {'type': 'Vector', 'x': x, 'y': y, 'z': z}
        elif struct_type == "Rotator":
            pitch = self.read_f32()
            yaw = self.read_f32()
            roll = self.read_f32()
            return {'type': 'Rotator', 'pitch': pitch, 'yaw': yaw, 'roll': roll}
        elif struct_type == "Quat":
            x = self.read_f32()
            y = self.read_f32()
            z = self.read_f32()
            w = self.read_f32()
            return {'type': 'Quat', 'x': x, 'y': y, 'z': z, 'w': w}
        elif struct_type == "Transform":
            props = {}
            while True:
                name, prop = self.read_property()
                if name is None:
                    break
                props[name] = prop
            return {'type': 'Transform', 'properties': props}
        elif struct_type == "LinearColor":
            r = self.read_f32()
            g = self.read_f32()
            b = self.read_f32()
            a = self.read_f32()
            return {'type': 'LinearColor', 'r': r, 'g': g, 'b': b, 'a': a}
        elif struct_type == "Color":
            b = self.read(1)[0]
            g = self.read(1)[0]
            r = self.read(1)[0]
            a = self.read(1)[0]
            return {'type': 'Color', 'r': r, 'g': g, 'b': b, 'a': a}
        elif struct_type == "Guid":
            return {'type': 'Guid', 'value': self.read_guid()}
        elif struct_type == "DateTime":
            ticks = self.read_i64()
            return {'type': 'DateTime', 'ticks': ticks}
        elif struct_type == "Timespan":
            ticks = self.read_i64()
            return {'type': 'Timespan', 'ticks': ticks}
        elif struct_type == "Vector2D":
            x = self.read_f32()
            y = self.read_f32()
            return {'type': 'Vector2D', 'x': x, 'y': y}
        elif struct_type == "IntPoint":
            x = self.read_i32()
            y = self.read_i32()
            return {'type': 'IntPoint', 'x': x, 'y': y}
        else:
            # Generic struct - read as property list
            props = {}
            while True:
                name, prop = self.read_property()
                if name is None:
                    break
                props[name] = prop
            return {'type': struct_type, 'properties': props}

    def read_array(self, array_type, size, prop_name=""):
        count = self.read_u32()
        if count == 0:
            return []
        
        if array_type == "StructProperty":
            # Struct arrays have extra header
            field_name = self.read_string()
            type_name = self.read_string()  # "StructProperty"
            elem_size = self.read_u64()
            struct_type = self.read_string()
            struct_guid = self.read_guid()
            self.read(1)  # terminator
            
            items = []
            for _ in range(count):
                item = self.read_struct(struct_type, 0)
                items.append(item)
            return items
        elif array_type == "IntProperty":
            return [self.read_i32() for _ in range(count)]
        elif array_type == "UInt32Property":
            return [self.read_u32() for _ in range(count)]
        elif array_type == "FloatProperty":
            return [self.read_f32() for _ in range(count)]
        elif array_type == "StrProperty" or array_type == "NameProperty":
            return [self.read_string() for _ in range(count)]
        elif array_type == "BoolProperty":
            return [self.read_bool() for _ in range(count)]
        elif array_type == "ByteProperty":
            return list(self.read(count))
        elif array_type == "EnumProperty":
            return [self.read_string() for _ in range(count)]
        elif array_type == "ObjectProperty":
            return [self.read_string() for _ in range(count)]
        elif array_type == "SoftObjectProperty":
            items = []
            for _ in range(count):
                asset = self.read_string()
                sub = self.read_string()
                items.append({'asset_path': asset, 'sub_path': sub})
            return items
        else:
            # Read remaining bytes for this array
            remaining = size - 4  # subtract count bytes already read
            raw = self.read(remaining)
            return f"<raw array [{array_type}] x{count}, {len(raw)} bytes>"

    def read_map(self, key_type, value_type, size):
        start = self.offset
        _zero = self.read_u32()  # number of removals (usually 0)
        count = self.read_u32()
        
        items = []
        try:
            for _ in range(count):
                key = self.read_map_type(key_type)
                val = self.read_map_type(value_type)
                items.append({'key': key, 'value': val})
        except Exception as e:
            # If map parsing fails, return raw
            remaining = size - (self.offset - start)
            if remaining > 0:
                self.read(remaining)
            items.append({'error': str(e)})
        
        return {'key_type': key_type, 'value_type': value_type, 'entries': items}

    def read_map_type(self, type_name):
        if type_name == "IntProperty":
            return self.read_i32()
        elif type_name == "StrProperty" or type_name == "NameProperty":
            return self.read_string()
        elif type_name == "FloatProperty":
            return self.read_f32()
        elif type_name == "BoolProperty":
            return self.read_bool()
        elif type_name == "EnumProperty":
            return self.read_string()
        elif type_name == "StructProperty":
            props = {}
            while True:
                name, prop = self.read_property()
                if name is None:
                    break
                props[name] = prop
            return props
        elif type_name == "ObjectProperty":
            return self.read_string()
        else:
            return f"<unknown map type: {type_name}>"

    def parse(self):
        header = self.read_header()
        
        # Read save game type
        save_game_type = self.read_string()
        header['save_game_class'] = save_game_type
        
        # Read properties
        properties = {}
        try:
            while self.offset < len(self.data):
                name, prop = self.read_property()
                if name is None:
                    break
                properties[name] = prop
        except Exception as e:
            properties['__parse_error__'] = {
                'error': str(e),
                'offset': self.offset,
                'total_size': len(self.data)
            }
        
        return {'header': header, 'properties': properties}


