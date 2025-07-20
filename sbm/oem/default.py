"""
Default OEM handler for the SBM tool.

This module provides a fallback handler for dealers that don't match any specific OEM.
"""

from .base import BaseOEMHandler


class DefaultHandler(BaseOEMHandler):
    """
    Default handler for dealers that don't match any specific OEM.
    
    Provides generic styles and patterns that work across most dealers.
    """

    def get_map_styles(self):
        """
        Get generic map styles.
        
        Returns:
            str: CSS/SCSS content for map styles
        """
        # Default map styles that work for most dealers
        return """
/* MAP ROW **************************************************/
#mapRow {
  position: relative;
  .mapwrap {
    height: 600px;
  }
}
#map-canvas {
  height: 100%;
}
/* DIRECTIONS BOX **************************************************/
#directionsBox {
  padding: 50px 0;
  text-align: left;
  width: 400px;
  position: absolute;
  top: 200px;
  left: 50px;
  background: #fff;
  text-align: left;
  color: #111;
  font-family: var(--heading-font-family);
  .getdirectionstext {
    display: inline-block;
    font-size: 24px;
    margin: 0;
  }
  .locationtext {
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 20px;
  }
  .address {
    margin-bottom: 20px;
  }
}
@media (max-width: 920px) {
  #mapRow {
    .mapwrap {
      height: 250px;
    }
    #directionsBox {
      width: unset;
      height: 100%;
      top: 0;
      left: 0;
      padding: 20px;
      max-width: 45%;
    }
  }
}"""

    def get_directions_styles(self):
        """
        Get generic direction box styles.
        
        Returns:
            str: CSS/SCSS content for directions box styles
        """
        # Use the same styles as map styles for default handler
        return self.get_map_styles()

    def get_brand_match_patterns(self):
        """
        Get patterns for identifying if a dealer belongs to this handler.
        
        Returns:
            list: Regular expression patterns for matching dealer brands
        """
        # This is a fallback handler, so it doesn't have specific patterns
        return []
