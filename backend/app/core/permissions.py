from enum import Enum


class Permission(str, Enum):
    READ_CHAT = "read:chat"
    WRITE_CHAT = "write:chat"
    DELETE_CHAT = "delete:chat"
    READ_DOCUMENT = "read:document"
    WRITE_DOCUMENT = "write:document"
    DELETE_DOCUMENT = "delete:document"
    READ_DRAFT = "read:draft"
    WRITE_DRAFT = "write:draft"
    ADMIN = "admin"


class Role(str, Enum):
    USER = "user"
    ADVOCATE = "advocate"
    LAW_FIRM = "law_firm"
    ADMIN = "admin"


ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.USER: [
        Permission.READ_CHAT,
        Permission.WRITE_CHAT,
        Permission.DELETE_CHAT,
        Permission.READ_DOCUMENT,
        Permission.WRITE_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.READ_DRAFT,
        Permission.WRITE_DRAFT,
    ],
    Role.ADVOCATE: [
        Permission.READ_CHAT,
        Permission.WRITE_CHAT,
        Permission.DELETE_CHAT,
        Permission.READ_DOCUMENT,
        Permission.WRITE_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.READ_DRAFT,
        Permission.WRITE_DRAFT,
    ],
    Role.LAW_FIRM: [
        Permission.READ_CHAT,
        Permission.WRITE_CHAT,
        Permission.DELETE_CHAT,
        Permission.READ_DOCUMENT,
        Permission.WRITE_DOCUMENT,
        Permission.DELETE_DOCUMENT,
        Permission.READ_DRAFT,
        Permission.WRITE_DRAFT,
    ],
    Role.ADMIN: [p for p in Permission],
}
