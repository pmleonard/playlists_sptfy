from analysis import ERA_TAGS
from flask import Blueprint, jsonify
from genre_analysis import GENRE_TAGS

bp = Blueprint("tag_groups", __name__, url_prefix="/api/tag-groups")


@bp.get("/")
def get_tag_groups():
    return jsonify({"genre_tags": sorted(GENRE_TAGS), "era_tags": sorted(ERA_TAGS)})
